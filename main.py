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


app = FastAPI(title="Brady Go Fund Me")

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
    "GET /test": RouteConfig(
        accepts=[
            PaymentOption(
                scheme="exact",
                price="$1.00",
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


@app.get("/test")
async def test_endpoint():
    return {
        "message": "Payment successful!",
        "amount": "1.00 USDC",
        "network": "Base",
    }
