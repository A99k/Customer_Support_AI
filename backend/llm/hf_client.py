"""
Thin wrapper around the Hugging Face Inference Providers API (via
huggingface_hub's InferenceClient) so every agent can call
`generate(system_prompt, user_prompt)` without worrying about auth, retries,
or error handling.
"""
import sys
from pathlib import Path

from huggingface_hub import InferenceClient
from huggingface_hub.errors import HfHubHTTPError

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from backend import config


class HFClient:
    def __init__(self, model: str = None):
        self.model = model or config.HF_MODEL
        if not config.HF_TOKEN:
            print("WARNING: HF_TOKEN is not set. Requests to the Hugging Face "
                  "Inference API will likely fail. Set it in your .env file.")
        # Model is passed per-request (see generate()), not here. Pinning it
        # at construction time can pin the client to the retired legacy
        # api-inference.huggingface.co host on some huggingface_hub versions;
        # passing it per-call routes through the current Inference Providers
        # gateway (router.huggingface.co) instead.
        self._client = InferenceClient(
            api_key=config.HF_TOKEN or None,
            provider=config.HF_PROVIDER,
        )

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = None,
        temperature: float = None,
    ) -> str:
        """Send a chat-style completion request and return the assistant's text.

        Falls back to a friendly error message instead of raising, so a single
        agent failure never crashes the whole /api/chat request.
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        try:
            completion = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens or config.HF_MAX_TOKENS,
                temperature=temperature or config.HF_TEMPERATURE,
            )
            return completion.choices[0].message.content.strip()
        except HfHubHTTPError as e:
            print(f"[HFClient] Hugging Face API error: {e}")
            return (
                "I'm having trouble reaching our AI model right now. "
                "Please try again in a moment, or type 'talk to a human' "
                "to reach a support representative."
            )
        except Exception as e:  # noqa: BLE001 - we want a safe fallback for any failure
            print(f"[HFClient] Unexpected error ({type(e).__name__}): {e}")
            hint = ""
            if "NameResolutionError" in str(e) or "getaddrinfo" in str(e) or "resolve" in str(e).lower():
                hint = (
                    " (This looks like a DNS/network issue reaching Hugging "
                    "Face — check your internet connection and that "
                    "huggingface.co / router.huggingface.co aren't blocked "
                    "by a firewall or VPN.)"
                )
                print(f"[HFClient] Possible connectivity problem.{hint}")
            return (
                "Something went wrong while generating a response. "
                "Please try again, or type 'talk to a human' for assistance."
            )


_client_instance: HFClient | None = None


def get_hf_client() -> HFClient:
    global _client_instance
    if _client_instance is None:
        _client_instance = HFClient()
    return _client_instance
