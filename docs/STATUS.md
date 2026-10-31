# TenderFender Deployment Status

- **Live URL**: https://cl5srhq2lbhpd775etjbpso6sy0fwrtt.lambda-url.ap-south-1.on.aws/
- **AWS Region**: ap-south-1
- **Stack Name**: tenderfender
- **Stack Status**: CREATE_COMPLETE
- **Teardown Command**: `make destroy` (or `aws cloudformation delete-stack --stack-name tenderfender`)

## Evidence Table

| Endpoint / Action | HTTP Status / Result |
|---|---|
| `GET /` | 200 (time_total=0.31s) |
| `GET /tenders/T-002` | 200 |
| `GET /api/health` | 200 |
| `GET /api/tenders` | 200 |
| `GET /api/tenders/T-001/analysis` | 200 (`decision_source`: `llm`, decision: `review`) |
| `GET /api/tenders/T-002/analysis` | 200 (`decision_source`: `llm`, decision: `escalate`) |
| `GET /api/tenders/T-003/analysis` | 200 (`decision_source`: `template`, decision: `clear`) |
| `GET /api/tenders/T-002/graph` | 200 |
| `GET /assets/index-C-w5bTHP.css` (gzip) | 200 (`content-encoding: gzip`) |
| `POST /api/tenders/T-001/atoms/CL2.1/confirm` | 200 (`formalization_status`: `confirmed`) |

## Tender Decision Sources

- **T-001**: `llm` (Reviewer verdict: supported)
- **T-002**: `llm` (Reviewer verdict: supported)
- **T-003**: `template`
