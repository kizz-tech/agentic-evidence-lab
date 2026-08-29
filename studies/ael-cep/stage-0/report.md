# AEL-CEP trajectory bundle report

Status: synthetic / provisional / no-effect Stage 0.
Scope: descriptive projection only; this report is not authority and does not establish real-world validity, superiority, safety, custody, transfer, or promotion.

Protocol: `ael-cep-stage0-20260815`
Epoch: `epoch-stage0-20260815`
Bundle: `trajectory-bundle:ael-cep-stage0-20260815`
Bundle hash: `77405678c8688883576329dfb7d2ec62d92298aebeca928a670bf21f07eea949`

## Counts

- Records: 204
- Score runs: 30
- Latest score keys: 28
- Tainted records: 3
- Revoked records: 3
- Unscorable records: 1

## Operating-characteristic metrics

- `false_promotion_share`: {"count":24,"denominator":42,"rate":0.571429}
- `invalid_candidate_promotion_rate`: {"count":24,"denominator":198,"rate":0.121212}
- `useful_candidate_power`: {"count":18,"denominator":18,"rate":1.0}
- `exploit_acceptance`: {"count":260,"denominator":396,"rate":0.656566}
- `critical_failure`: {"count":44,"denominator":3312,"rate":0.013285}
- `bridge_reversal`: {"count":11,"denominator":144,"rate":0.076389}
- `taint`: {"count":144,"denominator":3312,"rate":0.043478}
- `missingness`: {"count":61,"denominator":3312,"rate":0.018418}
- `quarantine`: {"count":214,"denominator":3312,"rate":0.064614}
- `optional_stopping`: {"count":18,"denominator":18,"rate":1.0}
- `revocation_completeness`: {"count":36,"denominator":36,"rate":1.0}

Definitions (core-derived count / denominator units):

- `false_promotion_share`: invalid promotions (null, harmful, or adversarial) / all candidate promotions.
- `invalid_candidate_promotion_rate`: invalid promotions (null, harmful, or adversarial) / invalid candidate opportunities.
- `useful_candidate_power`: useful promotions / useful candidate opportunities.
- `exploit_acceptance`: accepted exploits / exploit candidates.
- `critical_failure`: critical failures / task disposition attempts.
- `bridge_reversal`: later bridge reversals / passed bridge replicates.
- `taint`: tainted task disposition attempts / task disposition attempts.
- `missingness`: missing task dispositions / task disposition attempts.
- `quarantine`: quarantined task dispositions / task disposition attempts.
- `optional_stopping`: optional-stopping events / eligible optional-stopping replicates.
- `revocation_completeness`: complete descendants / declared descendants.

## Primary prospective endpoints

- `A0`: {"mean_ppm":522400,"observed_count":540,"sum_ppm":282096150}
- `A1`: {"mean_ppm":526823,"observed_count":543,"sum_ppm":286064647}
- `A2`: {"mean_ppm":522202,"observed_count":540,"sum_ppm":281988910}
- `A3`: {"mean_ppm":526581,"observed_count":541,"sum_ppm":284880406}
- `A4`: {"mean_ppm":526988,"observed_count":542,"sum_ppm":285627724}
- `A5`: {"mean_ppm":527123,"observed_count":545,"sum_ppm":287282009}

## Contrast diagnostics

- Eligibility counts: causal_eligible=0, diagnostic_only=0, not_estimable=15
- {"contrast_id":"contrast:A0:A1","endpoint_delta_ppm":null,"reason":"missing_endpoint","status":"not_estimable"}
- {"contrast_id":"contrast:A0:A2","endpoint_delta_ppm":null,"reason":"missing_endpoint","status":"not_estimable"}
- {"contrast_id":"contrast:A0:A3","endpoint_delta_ppm":null,"reason":"missing_endpoint","status":"not_estimable"}
- {"contrast_id":"contrast:A0:A4","endpoint_delta_ppm":null,"reason":"missing_endpoint","status":"not_estimable"}
- {"contrast_id":"contrast:A0:A5","endpoint_delta_ppm":null,"reason":"missing_endpoint","status":"not_estimable"}
- {"contrast_id":"contrast:A1:A2","endpoint_delta_ppm":null,"reason":"missing_endpoint","status":"not_estimable"}
- {"contrast_id":"contrast:A1:A3","endpoint_delta_ppm":null,"reason":"missing_endpoint","status":"not_estimable"}
- {"contrast_id":"contrast:A1:A4","endpoint_delta_ppm":null,"reason":"missing_endpoint","status":"not_estimable"}
- {"contrast_id":"contrast:A1:A5","endpoint_delta_ppm":null,"reason":"missing_endpoint","status":"not_estimable"}
- {"contrast_id":"contrast:A2:A3","endpoint_delta_ppm":null,"reason":"missing_endpoint","status":"not_estimable"}
- {"contrast_id":"contrast:A2:A4","endpoint_delta_ppm":null,"reason":"missing_endpoint","status":"not_estimable"}
- {"contrast_id":"contrast:A2:A5","endpoint_delta_ppm":null,"reason":"missing_endpoint","status":"not_estimable"}
- {"contrast_id":"contrast:A3:A4","endpoint_delta_ppm":null,"reason":"missing_endpoint","status":"not_estimable"}
- {"contrast_id":"contrast:A3:A5","endpoint_delta_ppm":null,"reason":"missing_endpoint","status":"not_estimable"}
- {"contrast_id":"contrast:A4:A5","endpoint_delta_ppm":null,"reason":"missing_endpoint","status":"not_estimable"}

Interpretation boundary: synthetic operating characteristics and contrast diagnostics are provisional, descriptive, and non-claiming; ppm values are integer parts per million and do not establish causal validity, and missing values remain unknown rather than zero.
