# QueryPDF Setup Guide

Follow these steps to set up and run the QueryPDF.

## Prerequisites

1. **Groq API Key**: Obtain from [Groq API Key](https://console.groq.com/playground).

## .env File Configuration

Create a `.env` file in the root directory of your project with the following content:

```plaintext
GROQ_API_KEY=your_groq_api_key_here
```

Replace `your_groq_api_key_here` with your actual API keys.

## Backend Setup

1. Open a terminal.
2. Install the required Python packages:

    ```sh
    pip install -r requirements.txt
    ```

3. Run the backend application:

    ```sh
    python app.py
    ```

## Frontend Setup

1. Open a new terminal.
2. Navigate to the `pdf-upload` directory:

    ```sh
    cd pdf-upload
    ```

3. Install the required Node.js packages:

    ```sh
    npm install
    ```

4. Start the frontend application:

    ```sh
    npm start
    ```

