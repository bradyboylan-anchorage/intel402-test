import os
from dotenv import load_dotenv
from fastapi import FastAPI
from x402.http.middleware.fastapi import PaymentMiddlewareASGI
from x402.http import HTTPFacilitatorClient, FacilitatorConfig, PaymentOption
from x402.http.facilitator_client_base import AuthHeaders, AuthProvider
from x402.http.types import RouteConfig
from x402.server import x402ResourceServer
from x402.mechanisms.evm.exact import ExactEvmServerScheme
from cdp.auth import get_auth_headers, GetAuthHeadersOptions

load_dotenv()

PAY_TO = os.environ["PAY_TO_ADDRESS"]
CDP_API_KEY_ID = os.environ["CDP_API_KEY_ID"]
CDP_API_KEY_SECRET = os.environ["CDP_API_KEY_SECRET"]

FACILITATOR_URL = "https://api.cdp.coinbase.com/platform/v2/x402"
FACILITATOR_HOST = "api.cdp.coinbase.com"


class CdpAuthProvider(AuthProvider):
    """Generates CDP JWT auth headers for each facilitator endpoint."""

    def _headers_for(self, method: str, path: str) -> dict[str, str]:
        return get_auth_headers(GetAuthHeadersOptions(
            api_key_id=CDP_API_KEY_ID,
            api_key_secret=CDP_API_KEY_SECRET,
            request_method=method,
            request_host=FACILITATOR_HOST,
            request_path=path,
        ))

    def get_auth_headers(self) -> AuthHeaders:
        return AuthHeaders(
            supported=self._headers_for("GET", "/platform/v2/x402/supported"),
            verify=self._headers_for("POST", "/platform/v2/x402/verify"),
            settle=self._headers_for("POST", "/platform/v2/x402/settle"),
        )


app = FastAPI(
    title="A Compliment from Brady via Slack",
    description="Pay Brady and receive a polite compliment via Slack. The more you pay, the better the compliment.",
)

# x402 payment server — Base mainnet via CDP facilitator
server = x402ResourceServer(
    HTTPFacilitatorClient(
        FacilitatorConfig(
            url=FACILITATOR_URL,
            auth_provider=CdpAuthProvider(),
        )
    )
)
server.register("eip155:8453", ExactEvmServerScheme())

# Protected routes
routes = {
    "GET /compliment": RouteConfig(
        accepts=[
            PaymentOption(
                scheme="exact",
                price="$1.00",
                network="eip155:8453",
                pay_to=PAY_TO,
            )
        ]
    ),
    "GET /nice-compliment": RouteConfig(
        accepts=[
            PaymentOption(
                scheme="exact",
                price="$10.00",
                network="eip155:8453",
                pay_to=PAY_TO,
            )
        ]
    ),
    "GET /amazing-compliment": RouteConfig(
        accepts=[
            PaymentOption(
                scheme="exact",
                price="$100.00",
                network="eip155:8453",
                pay_to=PAY_TO,
            )
        ]
    ),
}

app.add_middleware(PaymentMiddlewareASGI, routes=routes, server=server)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/compliment")
async def compliment():
    return {
        "tier": "compliment",
        "price": "1.00 USDC",
        "message": "Payment received! Brady will send you a polite compliment via Slack.",
    }


@app.get("/nice-compliment")
async def nice_compliment():
    return {
        "tier": "nice-compliment",
        "price": "10.00 USDC",
        "message": "Payment received! Brady will send you a thoughtful, personalized compliment via Slack.",
    }


@app.get("/amazing-compliment")
async def amazing_compliment():
    return {
        "tier": "amazing-compliment",
        "price": "100.00 USDC",
        "message": "Payment received! Brady will send you a legendary, life-affirming compliment via Slack. You will feel unstoppable.",
    }
