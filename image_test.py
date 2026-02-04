from google import genai

client = genai.Client()

my_file = client.files.upload(file="C:/Users/kpana/OneDrive/archescan/uploads/King_Tut_courtesy_LD_t1024.jpg")

response = client.models.generate_content(
    model="gemini-3-flash-preview",
    contents=[my_file, "Caption this image."],
)

print(response.text)