from fastapi import FastAPI, Request
import uvicorn

app = FastAPI()

@app.post("/upload")
async def upload_data(request: Request):
    # Read the raw streaming body (our CSV file)
    body = await request.body()
    
    # Save the received data to a local file
    with open("received_data.csv", "wb") as f:
        f.write(body)
    
    print(f"--- Received {len(body)} bytes of CSV data! ---")
    print(f"Successfully saved to received_data.csv")
    print("---------------------------------------------")
    
    return {"message": "Data received successfully!"}

def start():
    # Bind to 0.0.0.0 to listen on ALL network interfaces (Wi-Fi, Ethernet, localhost).
    # This is required so the ESP32 can reach this server over the local network!
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)

if __name__ == "__main__":
    start()
