# Copyright (c) Microsoft. All rights reserved.

import asyncio
import os

from semantic_kernel.agents import AgentGroupChat, ChatCompletionAgent
from semantic_kernel.agents.strategies import (
    KernelFunctionSelectionStrategy,
    KernelFunctionTerminationStrategy
)

from semantic_kernel.connectors.ai.open_ai.services.azure_chat_completion import AzureChatCompletion
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion, OpenAIChatPromptExecutionSettings
from semantic_kernel.connectors.openapi_plugin import OpenAPIFunctionExecutionParameters
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from semantic_kernel.contents.utils.author_role import AuthorRole
from semantic_kernel.functions.kernel_function_from_prompt import KernelFunctionFromPrompt
from semantic_kernel.kernel import Kernel

###################################################################
# The following sample demonstrates how to create a simple,       #
# agent group chat that utilizes An Art Director Chat Completion  #
# Agent along with a Copy Writer Chat Completion Agent to         #
# complete a task. The sample also shows how to specify a Kernel  #
# Function termination and selection strategy to determine when   #
# to end the chat or how to select the next agent to take a turn  #
# in the conversation.                                            #
###################################################################

prompt_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 
    "semantic-kernel",
    "prompts"
)

OFFERINGEXPERT_NAME = "TravelOfferingsExpert"
OFFERINGEXPERT_INSTRUCTIONS = open(os.path.join(prompt_path, "offering_expert_instructions.txt"), "r").read()

TRAVELAGENT_NAME = "TravelAgent"
TRAVELAGENT_INSTRUCTIONS = open(os.path.join(prompt_path, "travel_agent_instructions.txt"), "r").read()

TRAVELMANAGER_NAME = "TravelManager"
TRAVELMANAGER_INSTRUCTIONS = open(os.path.join(prompt_path, "travel_manager_instructions.txt"), "r").read()

def _create_kernel_with_chat_completion(service_id: str) -> Kernel:
    kernel = Kernel()
    kernel.add_service(OpenAIChatCompletion(service_id=service_id, env_file_path="./.env"))
    return kernel


async def main():
        
    travel_agent = ChatCompletionAgent(
        service_id="travelagent",
        kernel=_create_kernel_with_chat_completion("travelagent"),
        name=TRAVELAGENT_NAME,
        instructions=TRAVELAGENT_INSTRUCTIONS
    )
    

    execution_settings = OpenAIChatPromptExecutionSettings(
        function_choice_behavior=FunctionChoiceBehavior.Auto(auto_invoke=True)
    )
    
    travel_offerings_agent = ChatCompletionAgent(
        service_id="travelofferings",
        kernel=_create_kernel_with_chat_completion("travelofferings"),
        name=OFFERINGEXPERT_NAME,
        instructions=OFFERINGEXPERT_INSTRUCTIONS,
        execution_settings=execution_settings
    )    

    travel_offerings_agent.kernel.add_plugin_from_openapi(plugin_name="graphql_post", 
                                                openapi_document_path="./semantic-kernel/plugins/dab.yaml",                                                
                                                execution_settings=OpenAPIFunctionExecutionParameters(enable_dynamic_payload=True, ignore_non_compliant_errors=True, enable_payload_namespacing=True))
    

    travel_manager = ChatCompletionAgent(
        service_id="travelmanager",
        kernel=_create_kernel_with_chat_completion("travelmanager"),
        name=TRAVELMANAGER_NAME,
        instructions=TRAVELMANAGER_INSTRUCTIONS
    )

    termination_function = KernelFunctionFromPrompt(
        function_name="termination",
        prompt=f"""
        Determine if the travel plan has been approved by {TRAVELMANAGER_NAME}. 
        If so, respond with a single word: yes.

        History:

        {{{{$history}}}}
        """,
    )

    selection_function = KernelFunctionFromPrompt(
        function_name="selection",
        prompt=f"""
        Your job is to determine which participant takes the next turn in a conversation according to the action of the most recent participant.
        State only the name of the participant to take the next turn.

        Choose only from these participants:
        - {TRAVELMANAGER_NAME}
        - {OFFERINGEXPERT_NAME}
        - {TRAVELAGENT_NAME}

        Always follow these steps when selecting the next participant:
        1) After user input, it is {OFFERINGEXPERT_NAME}'s turn.
        2) After {OFFERINGEXPERT_NAME} replies, it's {TRAVELAGENT_NAME}'s turn to generate a plan for the given trip.
        3) After {TRAVELAGENT_NAME} replies, it's {TRAVELMANAGER_NAME}'s turn to review the plan.
        4) If the plan is approved, the conversation ends.
        5) If the plan is NOT approved, it's again {TRAVELAGENT_NAME}'s turn to provide an improved plan.
        6) Steps 3, 4, 5 and 6 are repeated until the plan is finally approved.
       
        History:
         {{{{$history}}}}
        """     
    )

    chat = AgentGroupChat(
        agents=[travel_offerings_agent, travel_agent, travel_manager],
        termination_strategy=KernelFunctionTerminationStrategy(
            agents=[travel_manager],
            function=termination_function,
            kernel=_create_kernel_with_chat_completion("termination"),
            result_parser=lambda result: str(result.value[0]).lower() == "yes",
            history_variable_name="history",
            maximum_iterations=10,
        ),
        selection_strategy=KernelFunctionSelectionStrategy(
            function=selection_function,
            kernel=_create_kernel_with_chat_completion("selection"),
            result_parser=lambda result: str(result.value[0]) if result.value is not None else TRAVELAGENT_NAME,
            agent_variable_name="agents",
            history_variable_name="history",
        ),
    )

    input = "A 3 day trip from Milan to Paris in April 2024"

    await chat.add_chat_message(ChatMessageContent(role=AuthorRole.USER, content=input))
    print(f"# {AuthorRole.USER}: '{input}'")

    async for content in chat.invoke():
        print(f"# {content.role} - {content.name or '*'}: '{content.content}'")

    print(f"# IS COMPLETE: {chat.is_complete}")


if __name__ == "__main__":
    asyncio.run(main())