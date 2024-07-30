import os
from openai import OpenAI
from openai import OpenAIError


# Initialize the OpenAI client
client = OpenAI(api_key="sk-proj-FS51Tc2KtbvEvK8Oyk4MT3BlbkFJBFImRbPphVVXcwWgb1EK")

def chat_with_gpt(prompt):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert precision agriculture technology assistant. The users that will be asking you questions will have an NDVI map, EVI map, SOil moisture map, Yield prediction map, and growth stage estimation"},
                {"role": "user", "content": prompt}
            ]
        )
        # Correctly access the content of the first choice
        return response.choices[0].message.content.strip()
    except OpenAIError as e:
        return f"An unexpected error occurred: {str(e)}"

if __name__ == "__main__":
    print("Welcome to the GPT-4o-mini Chatbot!")
    print("Type 'exit' to end the chat.\n")
    
    while True:
        user_input = input("You: ")
        if user_input.lower() == 'exit':
            print("Chat ended.")
            break
        output = chat_with_gpt(user_input)
        print(f"AI Expert: {output}")