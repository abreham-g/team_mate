
import os
import json
import openai
import uvicorn
import socketio
import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException
from typing import Dict, List
from weaviate import setup_weaviate_interface
from weaviate.weaviate_client import WeaviateClient
from weaviate.http_client import HttpClient, HttpHandler
from dotenv import load_dotenv


# Load environment variables from .env file
load_dotenv()

# Set up OpenAI API key
openai.api_key = os.getenv('OPENAI_API_KEY')

# FastAPI application
app = FastAPI()

# Socket.IO server
sio = socketio.AsyncServer(cors_allowed_origins="*", async_mode="asgi")
socket_app = socketio.ASGIApp(sio)
app.mount("/", socket_app)  

# Dictionary to store session data
sessions: Dict[str, List[Dict[str, str]]] = {}

# Weaviate Interface
WEAVIATE_URL = os.getenv('WEAVIATE_URL')
http_client = HttpClient(base_url=WEAVIATE_URL, headers={"Content-Type": "application/json"})
http_handler = HttpHandler(http_client=http_client)
weaviate_client = WeaviateClient(http_handler=http_handler)
weaviate_interface = setup_weaviate_interface()

def generate_response(user_message: str, context: str = None) -> str:
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": f"You are TeamMate. TeamMate is a helpful assistant. Use the following context: {context}",
            },
            {"role": "user", "content": user_message},
        ],
    )
    return response.choices[0].message.content

@app.get("/")
def read_root():
    return {"Hello": "World"}

@sio.on("connect")
async def connect(sid, env):
    print("New Client Connected to This id :" + " " + str(sid))

@sio.on("disconnect")
async def disconnect(sid):
    print("Client Disconnected: " + " " + str(sid))

@sio.on("connectionInit")
async def handle_connection_init(sid):
    await sio.emit("connectionAck", room=sid)

@sio.on("sessionInit")
async def handle_session_init(sid, data):
    print(f"===> Session {sid} initialized")
    session_id = data.get("sessionId")
    if session_id not in sessions:
        sessions[session_id] = []
    print(f"**** Session {session_id} initialized for {sid} session data: {sessions[session_id]}")
    await sio.emit("sessionInit", {"sessionId": session_id, "chatHistory": sessions[session_id]}, room=sid)

@sio.on("textMessage")
async def handle_chat_message(sid, data):
    print(f"Message from {sid}: {data}")
    session_id = data.get("sessionId")
    if session_id:
        if session_id not in sessions:
            raise Exception(f"Session {session_id} not found")
        received_message = {
            "id": data.get("id"),
            "message": data.get("message"),
            "isUserMessage": True,
            "timestamp": data.get("timestamp"),
        }
        sessions[session_id].append(received_message)

        # Generate response using OpenAI
        response_text = generate_response(data.get("message"))

        response_message = {
            "id": data.get("id") + "_response",
            "textResponse": response_text,
            "isUserMessage": False,
            "timestamp": data.get("timestamp"),
            "isComplete": True,
        }
        await sio.emit("textResponse", response_message, room=sid)
        sessions[session_id].append(response_message)

        print(f"Message from {sid} in session {session_id}: {data.get('message')}")
    else:
        print(f"No session ID provided by {sid}")

@app.post("/create-schema/")
async def create_schema():
    schema_path = "/home/abreham/Documents/GenAI/GenAI/team-mate/schema.json"
    try:
        with open(schema_path, 'r') as schema_file:
            schema_dict = json.load(schema_file)
        print("Schema content:", schema_dict)  # Log the schema content

        for class_info in schema_dict['classes']:
            try:
                print(f"Creating class: {class_info['class']}")  # Log class creation
                response = await weaviate_client.create_class(class_info)
                print(f"Class {class_info['class']} created successfully. Response: {response}")  # Log response

            except Exception as e:
                print(f"Error creating class {class_info['class']}: {e}")
                raise HTTPException(status_code=500, detail=f"Error creating class {class_info['class']}: {e}")

        return {"status": "Schema created successfully"}
    except FileNotFoundError as fnfe:
        print(f"Schema file not found: {str(fnfe)}")
        raise HTTPException(status_code=500, detail=f"Schema file not found: {str(fnfe)}")
    except Exception as e:
        print(f"Error creating schema: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/load-data/")
async def load_data(csv_file: UploadFile = File(...), class_name: str = "Job"):
    try:
        print("Received request to load data")
        csv_content = await csv_file.read()
        csv_path = "/home/abreham/Documents/GenAI/GenAI/team-mate/weaviate/all_nov_jobs.csv"
        with open(csv_path, "wb") as f:
            f.write(csv_content)
        print(f"CSV file saved to {csv_path}")
        success = await weaviate_client.load_data_from_csv(csv_path, class_name)
        if success:
            print("Data loaded successfully")
        else:
            print("Failed to load data")
        return {"status": "Data loaded successfully"} if success else {"status": "Failed to load data"}
    except Exception as e:
        print(f"Error loading data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/semantic-search/")
async def semantic_search(query: str, class_name: str = "Job"):
    try:
        results = await weaviate_interface.semantic_search(query, class_name)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    websocket_url = os.getenv('VITE_WEBSOCKET_URL')
    if websocket_url:
        port = int(websocket_url.split(':')[-1])
    else:
        port = 6789  # Default port if VITE_WEBSOCKET_URL is not set

    uvicorn.run("main:app", host="0.0.0.0", port=port, lifespan="on", reload=True)
