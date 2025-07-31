import json
import asyncio
from typing_extensions import Literal
import os

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import START, END, StateGraph
from langchain_core.output_parsers import JsonOutputParser


from mcp_server_deepresearcher.deepresearcher.state import SummaryState, SummaryStateInput, SummaryStateOutput
from mcp_server_deepresearcher.deepresearcher.prompts import (
    query_writer_instructions, 
    summarizer_instructions, 
    reflection_instructions, 
    get_current_date, 
    final_report_instructions
)
from mcp_server_deepresearcher.deepresearcher.utils import (
    clean_response, 
    create_mcp_tasks, 
    extract_source_info, 
    format_sources
)
import logging

logger = logging.getLogger(__name__)


# Nodes
class DeepResearcher:
    def __init__(self, LLM, tools: List[Union[Tool, StructuredTool]]):
        self.llm = LLM
        self.tools = tools
        self.graph = self._build_graph()
        logger.info(f"DeepResearcher initialized with LLM: {self.llm} and {self.tools} tools")

    def _build_graph(self):
        # Add nodes and edges
        builder = StateGraph(SummaryState, input=SummaryStateInput, output=SummaryStateOutput)
        builder.add_node("generate_query", self.generate_query)
        builder.add_node("web_research", self.web_research)
        builder.add_node("summarize_sources", self.summarize_sources)
        builder.add_node("reflect_on_summary", self.reflect_on_summary)
        builder.add_node("finalize_summary", self.finalize_summary)

        # Add edges
        builder.add_edge(START, "generate_query")
        builder.add_edge("generate_query", "web_research")
        builder.add_edge("web_research", "summarize_sources")
        builder.add_edge("summarize_sources", "reflect_on_summary")
        builder.add_conditional_edges("reflect_on_summary", self.route_research)
        builder.add_edge("finalize_summary", END)
        

        graph = builder.compile()
        logger.info("Graph compiled successfully")



        # Script to save the graph as an image file
        # Save the graph visualization as an image file
        logger.info("Saving graph as image")
        try:
            from IPython.display import Image
            
            # Get the directory of the current file
            output_dir = os.path.dirname(os.path.abspath(__file__))
            output_path = os.path.join(output_dir, "deep_researcher_graph.png")
            
            # Save the graph visualization as a PNG file
            try:
                # Use the appropriate method to save the graph
                # The get_graph() method accesses the internal graph representation
                graph_image = graph.get_graph().draw_mermaid_png()
                with open(output_path, "wb") as f:
                    f.write(graph_image)
                logger.info(f"Graph saved to {output_path}")
            except Exception as e:
                logger.error(f"Error saving graph: {e}")
        except Exception as e:
            logger.error(f"Error saving graph: {e}")
        return graph

    async def generate_query(self, state: SummaryState, config: RunnableConfig):
        """LangGraph node that generates a search query based on the research topic.
        
        Uses an LLM to create an optimized search query for web research based on
        the user's research topic. Supports both LMStudio and Ollama as LLM providers.
        
        Args:
            state: Current graph state containing the research topic
            config: Configuration for the runnable, including LLM provider settings
            
        Returns:
            Dictionary with state update, including search_query key containing the generated query
        """
        logger.info("--- Starting Generate Query Node ---")

        # Format the prompt
        current_date = get_current_date()
        formatted_prompt = query_writer_instructions.format(
            current_date=current_date,
            research_topic=state.research_topic
        )

        # Generate a query
        result = await self.llm.ainvoke(
            [SystemMessage(content=formatted_prompt),
            HumanMessage(content=f"Generate a query for web search:")]
        )
        
        # Get the content
        content = result.content
        # Parse response directly to dict using JsonOutputParser
        cleaned_response = clean_response(content)
        result = JsonOutputParser().parse(cleaned_response)

        # Get the query
        search_query = result['query']

        logger.info(f"Generated query: {search_query}")
     

        return {"search_query": search_query}

    # In deep_researcher/src/graph.py

    async def web_research(self, state: SummaryState, config: RunnableConfig):
        """
        LangGraph node that performs parallel web research using multiple MCP servers.
        
        Executes searches, correctly parses and aggregates the results, and formats
        them for further processing.
        """
        logger.info("--- Starting Parallel Web Research Node ---")
        
        # 1. Create and execute tasks in parallel
        tasks, task_names = create_mcp_tasks(self.tools, state.search_query)
        # return_exceptions=True is crucial for resilience
        parallel_results = await asyncio.gather(*tasks, return_exceptions=True)

        # 2. Process the results in a single, clean loop
        all_raw_content = []
        all_structured_sources = []

        for i, result in enumerate(parallel_results):
            task_name = task_names[i]
            
            if isinstance(result, Exception):
                print(f"  - Task '{task_name}' FAILED with error: {result}")
                # Optionally add error to raw content for LLM to know
                all_raw_content.append(f"Note: The search for '{task_name}' failed.")
                continue

            # This handles both string and tuple `(content, None)` results
            content = result[0] if isinstance(result, tuple) else result
            
            # If the content is a list, join it into a single string.
            if isinstance(content, list):
                content = "\n".join(map(str, content))
            
            # Ensure content is a string before stripping
            content = str(content)
            
            if not content or not content.strip():
                print(f"  - Task '{task_name}' succeeded but returned empty content.")
                continue

            print(f"  - Task '{task_name}' completed successfully.")
            all_raw_content.append(content)
            
            # Use helper to get structured info for citations
            source_info = extract_source_info(content, task_name)
            all_structured_sources.append(source_info)

        # 3. Aggregate and format the final outputs
        # A single string with all the raw content for the LLM
        search_str = "\n\n---\n\n".join(all_raw_content)
        
        # A single, formatted string of numbered sources for citation
        formatted_sources_str = format_sources(all_structured_sources)

        logger.info("--- Web Research Node Finished ---")
        
        # 4. Return the correctly structured dictionary
        logger.info(f"Returning web research results: {search_str}")
 
        return {
            "sources_gathered": [formatted_sources_str], 
            "research_loop_count": state.research_loop_count + 1, 
            "web_research_results": [search_str]
        }

    async def summarize_sources(self, state: SummaryState, config: RunnableConfig):
        """LangGraph node that summarizes web research results.
        
        Uses an LLM to create or update a running summary based on the newest web research 
        results, integrating them with any existing summary.
        
        Args:
            state: Current graph state containing research topic, running summary,
                and web research results
            config: Configuration for the runnable, including LLM provider settings
            
        Returns:
            Dictionary with state update, including running_summary key containing the updated summary
        """
        logger.info("--- Starting Summarize Sources Node ---")

        # Existing summary
        existing_summary = state.running_summary
        logger.info(f"Existing summary: {existing_summary}")

        # Most recent web research
        most_recent_web_research = state.web_research_results[-1]

        # Build the human message
        if existing_summary:
            human_message_content = (
                f"<Existing Summary> \n {existing_summary} \n <Existing Summary>\n\n"
                f"<New Context> \n {most_recent_web_research} \n <New Context>"
                f"Update the Existing Summary with the New Context on this topic: \n <User Input> \n {state.research_topic} \n <User Input>\n\n"
            )
        else:
            human_message_content = (
                f"<Context> \n {most_recent_web_research} \n <Context>"
                f"Create a Summary using the Context on this topic: \n <User Input> \n {state.research_topic} \n <User Input>\n\n"
            )

        # Run the LLM
        result = await self.llm.ainvoke(
            [SystemMessage(content=summarizer_instructions),
            HumanMessage(content=human_message_content)]
        )
    
        # Strip thinking tokens if configured
        running_summary = result.content

        logger.info(f"Running summary: {running_summary}")



        return {"running_summary": running_summary}

    async def reflect_on_summary(self, state: SummaryState, config: RunnableConfig):
        """LangGraph node that identifies knowledge gaps and generates follow-up queries.
        
        Analyzes the current summary to identify areas for further research and generates
        a new search query to address those gaps. Uses structured output to extract
        the follow-up query in JSON format.
        
        Args:
            state: Current graph state containing the running summary and research topic
            config: Configuration for the runnable, including LLM provider settings
            
        Returns:
            Dictionary with state update, including search_query key containing the generated follow-up query
        """
        logger.info("--- Starting Reflect on Summary Node ---")

        result = await self.llm.ainvoke(
            [SystemMessage(content=reflection_instructions.format(research_topic=state.research_topic)),
            HumanMessage(content=f"Reflect on our existing knowledge: \n === \n {state.running_summary}, \n === \n And now identify a knowledge gap and generate a follow-up web search query:")]
        )
            

        # Strip thinking tokens if configured
        try:
            # Try to parse as JSON first
            reflection_content = json.loads(result.content)
            logger.info(f"Reflection content: {reflection_content}")
      
            # Get the follow-up query
            query = reflection_content.get('follow_up_query')
            # Check if query is None or empty
            if not query:
                # Use a fallback query
                return {"search_query": f"Tell me more about {state.research_topic}"}
            return {"search_query": query}
        except (json.JSONDecodeError, KeyError, AttributeError):
            # If parsing fails or the key is not found, use a fallback query
            return {"search_query": f"Tell me more about {state.research_topic}"}

    async def finalize_summary(self, state: SummaryState):
        """
        LangGraph node that finalizes the research summary.

        This node cleans and deduplicates the gathered sources, then uses an LLM to
        generate a final, beautifully formatted research report with a title,
        executive summary, and key findings, followed by a clean list of sources.
        """
        logger.info("--- Starting Finalize Summary Node ---")

        # 1. Clean and Deduplicate Sources
        seen_sources = set()
        unique_sources = []
        
        for source_str in state.sources_gathered:
            for line in source_str.split('\n'):
                line = line.strip()
                if not line or line == '{}':  # Skip empty or invalid
                    continue

                # Attempt to extract a clean URL and title
                try:
                    # Handle JSON data from twitter/apidojo
                    if line.startswith("[apidojo"):
                        json_part = line.split("] ")[1]
                        data = json.loads(json_part)
                        url = data.get("url") or data.get("twitterUrl")
                        text = data.get("text", "No title available").split('\n')[0]
                        if url and url not in seen_sources:
                            unique_sources.append({"title": text, "url": url})
                            seen_sources.add(url)
                    else:
                        # Handle other formats like [tool] title (url)
                        parts = line.split("] ")
                        if len(parts) > 1:
                            content = parts[1]
                            # Extract URL which is often at the end in parentheses
                            url_start = content.rfind('(')
                            if url_start != -1:
                                url = content[url_start+1:-1]
                                title = content[:url_start].strip()
                                if url and url not in seen_sources:
                                    unique_sources.append({"title": title, "url": url})
                                    seen_sources.add(url)
                except (json.JSONDecodeError, IndexError, AttributeError) as e:
                    logger.warning(f"Could not parse source line: '{line}'. Error: {e}")

        # 2. Use the LLM to generate the structured report as JSON
        human_message_content = (
            f"<Existing Summary> \n {state.running_summary} \n <Existing Summary>\n\n"
            "Please generate the final report based on the above summary."
        )

        result = await self.llm.ainvoke(
            [SystemMessage(content=final_report_instructions),
            HumanMessage(content=human_message_content)]
        )
        logger.info(f"Final report: {result.content}")
  
        
        try:
            report_data = json.loads(result.content)
        except json.JSONDecodeError:
            logger.error("Failed to parse LLM output as JSON. Using fallback.")
            report_data = {
                "title": "Research Report",
                "executive_summary": state.running_summary,
                "key_findings": []
            }

        # 3. Add sources to the structured data
        report_data["sources"] = unique_sources

        return {"running_summary": report_data}

    async def route_research(self, state: SummaryState, config: RunnableConfig) -> Literal["finalize_summary", "web_research"]:
        """LangGraph routing function that determines the next step in the research flow.
        
        Controls the research loop by deciding whether to continue gathering information
        or to finalize the summary based on the configured maximum number of research loops.
        
        Args:
            state: Current graph state containing the research loop count
            config: Configuration for the runnable, including max_web_research_loops setting
            
        Returns:
            String literal indicating the next node to visit ("web_research" or "finalize_summary")
        """
        logger.info("--- Starting Route Research Node ---")
        configurable = config.get("configurable", {})
        max_loops = configurable.get("max_web_research_loops", 2)  # Default to 2 loops
        if state.research_loop_count <= max_loops:
            logger.info(f"Research loop count: {state.research_loop_count} is less than max loops: {max_loops}, returning to web_research")
            return "web_research"
        else:
            logger.info(f"Research loop count: {state.research_loop_count} is greater than max loops: {max_loops}, returning to finalize_summary")
            return "finalize_summary"



