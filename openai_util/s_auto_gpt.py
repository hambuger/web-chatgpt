import json
import openai
from openai import OpenAIError
import os
from util.redis.redis_client import api_key_manager
from config.global_logger import logger
from openai_util.function_call.funcation_invoke import invoke_function, get_invoke_method_info_by_name, do_step_by_step


def create_chat_completion(user_content, function_msg, functions=None, function_call=None):
    try:
        openai.api_key = api_key_manager.get_openai_key()
        use_model = os.getenv('DEFAULT_CHAT_MODEL', 'gpt-3.5-turbo')
        messages = [{"role": "user", "content": user_content}]
        if function_msg:
            messages.append(function_msg)
            use_model = os.getenv('GET_METHOD_ARGUMENTS_MODEL', 'gpt-3.5-turbo-0613')
        if not function_call:
            function_call = 'none'
        if not functions:
            return openai.ChatCompletion.create(
                model=use_model,
                messages=messages,
                temperature=0
            )
        use_model = os.getenv('GET_INVOKE_METHOD_MODEL', 'gpt-3.5-turbo-16k')
        return openai.ChatCompletion.create(
            model=use_model,
            messages=messages,
            functions=functions,
            function_call=function_call,
            temperature=0
        )
    except OpenAIError as e:
        logger.info(f"user_content: {user_content}, function_msg: {function_msg}, functions: {functions}")
        logger.error(e.message)
        return None


def get_function_result_from_openai_response(response):
    message = response.choices[0].message
    if not message.get("function_call"):
        if not message.get('content'):
            return None, message.get('content')
        else:
            return None, None
    else:
        message.get("function_call")
        function_name = message["function_call"]["name"]
        function_args = message["function_call"]["arguments"]
        logger.info("invoke method：" + function_name + " args：" + str(function_args))
        return function_name, invoke_function(function_name, function_args)


def run_conversation_v1(user_content):
    selection_response = create_chat_completion(user_content, None,
                                                [get_invoke_method_info_by_name("get_invoke_method_info")],
                                                "auto")
    logger.info("1:" + json.dumps(selection_response))
    function_name, function_result = get_function_result_from_openai_response(selection_response)
    if not function_name:
        return selection_response
    execution_response = create_chat_completion(user_content, None, [function_result], "auto")
    logger.info("2:" + json.dumps(execution_response))
    function_name, function_result = get_function_result_from_openai_response(execution_response)
    if not function_name:
        return execution_response
    final_response = create_chat_completion(user_content, {"role": "function", "name": function_name,
                                                           "content": json.dumps(function_result), },
                                            None,
                                            "auto")
    logger.info("3:" + json.dumps(final_response))
    return final_response


def create_chat_completion_with_msg(new_msg, functions):
    try:
        if not functions:
            openai.api_key = api_key_manager.get_openai_key()
            return openai.ChatCompletion.create(
                model=os.getenv('GET_METHOD_ARGUMENTS_MODEL', 'gpt-3.5-turbo-0613'),
                messages=new_msg,
                temperature=0
            )
        openai.api_key = api_key_manager.get_openai_key()
        return openai.ChatCompletion.create(
            model=os.getenv('GET_METHOD_ARGUMENTS_MODEL', 'gpt-3.5-turbo-0613'),
            messages=new_msg,
            functions=functions,
            function_call="auto",
            temperature=0
        )
    except OpenAIError as e:
        logger.error(e.message)
        return None


def run_single_step_chat(messages, functions):
    try:
        new_msg = list(messages)
        get_arguments_response = create_chat_completion_with_msg(new_msg, functions)
        # logger.info("get_arguments_response:{}".format(json.dumps(get_arguments_response)))
        function_name, function_result = get_function_result_from_openai_response(get_arguments_response)
        if not function_name:
            return get_arguments_response
        new_msg.append({"role": "function", "name": function_name,
                        "content": json.dumps(function_result)})
        final_response = create_chat_completion_with_msg(new_msg,
                                                         None)
        # logger.info("final_response:{}".format(json.dumps(final_response)))
        messages.append(final_response["choices"][0]["message"])
        return final_response
    except OpenAIError as e:
        logger.exception(e)
        return None


def run_conversation_v2(user_content):
    # Analyze the user's instructions into detailed operation steps through chatgpt
    step_response = create_chat_completion(user_content, None,
                                           [do_step_by_step()],
                                           "auto")
    # print([do_step_by_step()])
    message = step_response["choices"][0]["message"]
    if not message.get("function_call"):
        # logger.info("response:{}".format(step_response["choices"][0]["message"]['content']))
        return message['content']
    function_args = message["function_call"]["arguments"]
    steps = json.loads(function_args)['steps']
    # order by step_order asc
    steps.sort(key=lambda x: x['step_order'])
    messages = [{"role": "system",
                 "content": "You are an advanced robot, and you can do almost anything that humans ask you to do."},
                {"role": "user", "content": user_content}]
    # loop through each step
    order_step_response = None
    for index, step in enumerate(steps):
        order_step_response = run_single_step_chat(messages, [get_invoke_method_info_by_name(step['step_method'])])
        # logger.info(
        #     "order:{}, response:{}".format(index, order_step_response["choices"][0]["message"]['content']))
    if order_step_response:
        return order_step_response["choices"][0]["message"]['content']
    else:
        return '出错了'


# print(run_conversation_v2("导航到杭州"))
# print(run_conversation_v2("如果杭州天气好的话，打电话给gongqi"))
# print(run_conversation_v2(
#     "https://images.unsplash.com/photo-1618843479313-40f8afb4b4d8?ixlib=rb-4.0.3&ixid=MnwxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8&auto=format&fit=crop&w=2070&q=80  这个图片里车的品牌是什么"))