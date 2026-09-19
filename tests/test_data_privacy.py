import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUTH_SCHEMAS = ROOT / "services/auth-service/app/schemas.py"
AUTH_ROUTES = ROOT / "services/auth-service/app/routes/auth.py"
TRANSACTION_ROUTES = ROOT / "services/transactions-service/app/routes/transactions.py"
ACCOUNT_ROUTES = ROOT / "services/transactions-service/app/routes/accounts.py"
NGINX_CONFIG = ROOT / "infra/nginx/bankcore.conf"


class DataPrivacyContractTests(unittest.TestCase):
    def test_pix_resolution_dto_is_minimal_and_internal(self):
        tree = ast.parse(AUTH_SCHEMAS.read_text(encoding="utf-8"))
        response = next(
            node for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == "PixResolutionResponse"
        )
        fields = {
            node.target.id
            for node in response.body
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
        }
        self.assertEqual(fields, {"destination_user_id"})

        routes = AUTH_ROUTES.read_text(encoding="utf-8")
        self.assertIn(
            '@router.post("/internal/pix/resolve", response_model=PixResolutionResponse, include_in_schema=False)',
            routes,
        )
        self.assertIn("Depends(require_internal_service)", routes)
        self.assertNotIn("DirectoryLookupResponse", routes)

    def test_pix_key_stays_in_internal_request_body(self):
        routes = TRANSACTION_ROUTES.read_text(encoding="utf-8")
        self.assertIn('f"{settings.AUTH_SERVICE_URL}/auth/internal/pix/resolve"', routes)
        self.assertIn('json={"pix_key": tax_id}', routes)
        self.assertNotIn("/auth/directory/", routes)
        self.assertNotIn('detail=f"Falha ao consultar diretório Pix: {exc}"', routes)

    def test_internal_prefix_is_hidden_at_gateway(self):
        nginx = NGINX_CONFIG.read_text(encoding="utf-8")
        self.assertIn('location ^~ /auth/internal/ { return 404; }', nginx)
        self.assertIn('location = /auth/internal-token { return 404; }', nginx)

    def test_legacy_directory_contract_is_absent_from_clients_and_services(self):
        roots = (ROOT / "apps", ROOT / "services", ROOT / "infra", ROOT / "docs")
        for root in roots:
            for path in root.rglob("*"):
                if path.is_file() and path.suffix not in {".pyc", ".class"}:
                    self.assertNotIn("/auth/directory", path.read_text(encoding="utf-8", errors="ignore"))

    def test_internal_destination_identifier_is_not_in_public_layers(self):
        roots = (ROOT / "apps", ROOT / "infra", ROOT / "docs")
        for root in roots:
            for path in root.rglob("*"):
                if path.is_file() and path.suffix not in {".pyc", ".class"}:
                    self.assertNotIn("destination_user_id", path.read_text(encoding="utf-8", errors="ignore"))

    def test_account_endpoints_keep_server_side_ownership_checks(self):
        routes = ACCOUNT_ROUTES.read_text(encoding="utf-8")
        self.assertIn("def _owned_or_404", routes)
        self.assertIn("acc.user_id != user_id", routes)
        self.assertGreaterEqual(routes.count("_owned_or_404("), 3)
        self.assertIn('raise HTTPException(status_code=403, detail="Não é permitido operar a conta de outro correntista.")', routes)

    def test_public_pix_errors_are_uniform(self):
        routes = TRANSACTION_ROUTES.read_text(encoding="utf-8")
        self.assertIn('PIX_DESTINATION_NOT_FOUND = "Destinatário não encontrado."', routes)
        self.assertNotIn("usuário existe", routes.lower())
        self.assertNotIn("ainda não possui conta", routes.lower())


if __name__ == "__main__":
    unittest.main()
