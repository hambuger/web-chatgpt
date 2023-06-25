# import requests
# import torch
# from PIL import Image
# from transformers import BlipProcessor, BlipForConditionalGeneration
#
# image_to_text_model = "Salesforce/blip-image-captioning-large"
# device = 'cuda' if torch.cuda.is_available() else 'cpu'
# processor = BlipProcessor.from_pretrained(image_to_text_model)
# model = BlipForConditionalGeneration.from_pretrained(image_to_text_model).to(device)
#
#
# def describe_image(image_url: str, prompt: str):
#     image_object = Image.open(requests.get(image_url, stream=True).raw).convert('RGB')
#     inputs = processor(image_object, prompt, return_tensors="pt").to(device)
#     outputs = model.generate(**inputs)
#     return processor.decode(outputs[0], skip_special_tokens=True)
#
#
# print(describe_image(
#     'https://images.unsplash.com/photo-1618843479313-40f8afb4b4d8?ixlib=rb-4.0.3&ixid=MnwxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8&auto=format&fit=crop&w=2070&q=80',
#     'the brand of the car in the picture is '))

from PIL import Image
import requests
from transformers import AutoProcessor, BlipForQuestionAnswering
from openai_util.function_call.openaifunc_decorator import openai_func

model = BlipForQuestionAnswering.from_pretrained("Salesforce/blip-vqa-base")
processor = AutoProcessor.from_pretrained("Salesforce/blip-vqa-base")


@openai_func
def answer_by_image_url(image_url: str, prompt: str):
    """
    Answer according to the user's description and picture url

    :param image_url:URL of the picture
    :param prompt:user tips
    :return:generated description
    """
    image = Image.open(requests.get(image_url, stream=True).raw)
    inputs = processor(images=image, text=prompt, return_tensors="pt")
    return processor.decode(model.generate(**inputs, max_length=4000)[0], skip_special_tokens=True)
