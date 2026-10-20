import requests

ALLOWED_MODELS = {
    "gpt-4.1-mini",
    "gpt-4.1",
    "gpt-4.1-nano",
    "gpt-5-mini",
    "gpt-5",
}


@service(supports_response="only")
def openai_text(prompt=None, model="gpt-4.1-mini", return_response=True):
    """yaml
    name: OpenAI API Prompt
    description: Send a text prompt to OpenAI API and return the AI reply. Put the openai_api_key in secrets.yaml

    fields:
      prompt:
        name: Prompt
        required: true
        selector:
          text:

      model:
        name: Model
        default: gpt-4.1-mini
        required: true
        selector:
          select:
            options:
                - gpt-4.1-mini
                - gpt-4.1
                - gpt-4.1-nano
                - gpt-5-mini
                - gpt-5

    response:
      text:
        description: AI response
      status:
        description: HTTP status code
      error:
        description: Error message
    """

    # validate model
    if model not in ALLOWED_MODELS:
        model = "gpt-4.1-mini"

    try:
        api_key = pyscript.config.get("openai_api_key")

        r = task.executor(
            requests.post,
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "input": prompt or "say hello",
            },
            timeout=60,
        )

        data = r.json()

        text = data.get("output_text")
        if not text:
            try:
                text = data["output"][0]["content"][0]["text"]
            except Exception:
                text = ""

        return {
            "text": text,
            "status": r.status_code,
            "error": "" if r.ok else str(data),
        }

    except Exception as e:
        return {
            "text": "",
            "status": 0,
            "error": f"{type(e).__name__}: {e}",
        }
