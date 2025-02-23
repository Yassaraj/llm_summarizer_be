from exceptiongroup import catch
from google import genai
from google.genai import types
import fitz
import json
import os
from dotenv import load_dotenv
import logging


#Create log file
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()  # Print logs to the console
    ]
)

load_dotenv()

# Global access variables
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
PROMPT_TEMPLATE = 'Act as an experienced summarization specialist and Generate a concise summary under 80 words relevant to the domain of the given text and also extract the 5 most relevant keywords from the text while ensuring at least 4 of the extracted keywords appear in the generated summary as well. Return the output exclusively as a valid JSON object with the following structure:/n{{/n"summary": "Concise summary of the text (under 80 words)",/n"keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"]/n}}/nEnsure that only the JSON object is returned, with no extra characters, text, or formatting./nIf the text lacks sufficient information to be concisely summarized, simply return the output in the given JSON format where the values are messages stating "insufficient information"/nText:```{content}```'


def extract_text_and_images(pdf_path):
    """Extracts the text page wise and the number of images"""
    try:
        doc = fitz.open(pdf_path)
        pages_data = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text")
            num_images = len(page.get_images(full=True))
            pages_data.append({"page_num": page_num + 1, "content": text, "num_images": num_images})
        return pages_data

    except Exception as e:
        logging.error(f"Error reading pdf : {e}")
        return []


def get_gemini_response(prompt):
    """Calls the LLM api key and prompts for the response"""
    try:
        client = genai.Client(api_key=GOOGLE_API_KEY)
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1
            )
        )
        return response.text

    except Exception as e:
        logging.error(f"Error in LLM api call : {e}")
        return None


def extract_json(text):
    """Extract and validating the JSON object from the returned LLM response"""
    try:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or start > end:
            return None
        json_str = text[start:end + 1]
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logging.error(f"Error in JSON extraction process : {e}")
        return None

def retry_function(prompt, max_retries=3):
    """Retries up to max_retries times to get a valid JSON response"""
    try:
        for attempt in range(max_retries):
            response = get_gemini_response(prompt)
            extracted_json = extract_json(response)
            if extracted_json is not None:
                return extracted_json
            print(f"Attempt {attempt + 1}: Invalid response, retrying...")
        return None
    except Exception as e:
        logging.error(f"Error in retry process : {e}")
        return None

def get_constructed_summary_and_keywords(pdf_path):
    """
    Loops the extracted text page wise and generates a summary & keywords for each page
    Returns a list of dictionaries containing the page number, summary, and keywords
    """
    try:
        pdf_data = extract_text_and_images(pdf_path)
        response_data = []

        for page in pdf_data :
            page_number, page_content, image_count = page["page_num"], page["content"], page["num_images"]
            if len(page_content.split()) < 80:
                response_data.append({
                    "page_number" : page_number,
                    "summary" : "The available content is insufficient to create a meaningful summary.",
                    "keywords" : "Not enough content to extract keywords in this page."
                })
                continue

            prompt = PROMPT_TEMPLATE.format(content=page_content)
            response = retry_function(prompt,2)
            if response:
                if image_count==0:
                    summary= response["summary"]
                else:
                    summary = f'{response["summary"]}\n\n Note that this page contains {image_count} images which were not considered in the creation of the summary'

                response_data.append({
                    "page_number": page_number,
                    "summary": summary,
                    "keywords": response["keywords"]
                })
            else:
                response_data.append({
                    "page_number": page_number,
                    "summary": "Sorry! There was some trouble retrieving the summary from the LLM :(",
                    "keywords": "Sorry! We encountered a problem retrieving the keywords."
                })
        return response_data
    except Exception as e:
        logging.error(f"Error in the main process : {e}")
        return None

#result = get_constructed_summary_and_keywords(r"C:\Users\Development\Innodata\pdf-summarization-be\data\pdf.pdf")
#result = get_constructed_summary_and_keywords(r"C:\Users\Development\Innodata\pdf-summarization-be\main.py")




