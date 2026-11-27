# Persona training plan

This plan gives each persona a challenge order, the Microsoft Learn training to take along the way, and a certification to aim for. Learn titles, lengths, exam skills and credentials were checked on 2026-11-27.

## Personas and paths

| Persona | Starting point, from the [README](../README.md) | Adoption path |
|---|---|---|
| Platform engineer | Standing up Fabric for a regulated enterprise | A, governance-first |
| Fabric admin | Moving from ClickOps to Git-driven governance | C, AI-forward |
| Data engineer | Landing lakehouses, warehouses and notebooks inside a governance frame | B, delivery-first |

The paths are in [section 5 of the challenges overview](challenges-overview.md#5-suggested-adoption-paths). Each persona below adds the new challenges that fit it, and [Where challenges 09 to 13 fit](#where-challenges-09-to-13-fit) lists their prerequisites. A team that covers all three personas follows path D and places 09 to 13 by that table.

## Platform engineer

Path A proves control before workloads scale. Add challenge 11 after 01, so the network rules exist before data lands. Add 09 and 13 after 03, so the catalog metadata and the Purview transition assessment are done before 04 grants access. Purview Data Governance is retiring; support ends 12 November 2027.

**Order:** 00 → 01 → 11 → 03 → 09 → 13 → 04 → 07 → Capstone

**Learn training:**

- Before 03, the [Secure and govern analytics data in Microsoft Fabric](https://learn.microsoft.com/training/paths/secure-govern-analytics-data/) learning path (188 min). It covers the Fabric security model, workspace and item permissions, warehouse security, sensitivity labels and endorsement.
- Before 07, [Monitor activities in Microsoft Fabric](https://learn.microsoft.com/training/modules/monitor-fabric-items/) (61 min).
- For 11, the network security docs in the challenge's references.

**Certification:** DP-700. Add SC-401 if you own sensitivity labels and DLP.

## Fabric admin

Path C puts guardrails in place before the first data agent ships in 06. Add challenge 12 after 03 to manage tenant settings and policies as code, and 10 after 04 to put OneLake security roles in Git.

**Order:** 00 → 01 → 02 → 03 → 12 → 04 → 10 → 06 → Capstone

**Learn training:**

- Before 01, the [Manage a Microsoft Fabric environment](https://learn.microsoft.com/training/paths/manage-microsoft-fabric-environment/) learning path (177 min). It covers CI/CD with Git integration and deployment pipelines, the monitoring hub, and workspace and item permissions.
- Before 03, [Govern analytics data in Microsoft Fabric](https://learn.microsoft.com/training/modules/fabric-govern-analytics-data/) (44 min). It covers sensitivity labels, endorsement and documenting data assets.
- Before 06, [Implement Microsoft Fabric Data Agents (chat with your data)](https://learn.microsoft.com/training/modules/implement-fabric-data-agents/) (55 min).

**Certification:** DP-600 if Power BI semantic models are in scope, DP-700 otherwise. Add SC-401 if you own sensitivity labels and DLP.

## Data engineer

Path B ships a governed medallion stack first and adds access and audit in a second wave. If your team manages the data access roles on its lakehouses, add challenge 10 to the second wave, after 04.

**Order:** 00 → 01 → 02 → 05 → 08 → Capstone, then 04 → 10 → 07

**Learn training:**

- Before 02, [Implement continuous integration and continuous delivery (CI/CD) in Microsoft Fabric](https://learn.microsoft.com/training/modules/implement-cicd-in-fabric/) (46 min). Its deployment pipelines unit also prepares you for 08.
- Before 05, [Organize a Fabric lakehouse using medallion architecture design](https://learn.microsoft.com/training/modules/describe-medallion-architecture/) (71 min).
- Before the second wave, [Secure data access in Microsoft Fabric](https://learn.microsoft.com/training/modules/secure-data-access-in-fabric/) (70 min).

**Certification:** DP-700.

## Where challenges 09 to 13 fit

Place each one after its prerequisites. The last column shows where this plan puts it.

| Challenge | Prerequisites | Placed in |
|---|---|---|
| [09 — OneLake catalog metadata](../challenges/09-onelake-catalog-metadata/challenge.md) | 00, 01, 03 | Platform engineer, after 03 |
| [10 — OneLake security as code](../challenges/10-onelake-security-as-code/challenge.md) | 00, 01, 02, 04 | Fabric admin, after 04; data engineer, second wave |
| [11 — Network exfiltration guardrails](../challenges/11-network-exfiltration-guardrails/challenge.md) | 00, 01 | Platform engineer, after 01 |
| [12 — Tenant settings and policies as code](../challenges/12-tenant-settings-policies-as-code/challenge.md) | 00, 01, 03 | Fabric admin, after 03 |
| [13 — Purview transition assessment](../challenges/13-purview-transition-assessment/challenge.md) | 00, 01, 03, 09 | Platform engineer, after 09 |

## Certifications

| Certification | Exam | Governance skills measured |
|---|---|---|
| [Fabric Analytics Engineer Associate](https://learn.microsoft.com/credentials/certifications/fabric-analytics-engineer-associate/) | [DP-600](https://learn.microsoft.com/credentials/certifications/resources/study-guides/dp-600) | Implement security and governance: workspace and item access controls; row, column, object and file-level access; sensitivity labels; endorsement. It's part of "Maintain a data analytics solution" (25–30%). |
| [Fabric Data Engineer Associate](https://learn.microsoft.com/credentials/certifications/fabric-data-engineer-associate/) | [DP-700](https://learn.microsoft.com/credentials/certifications/resources/study-guides/dp-700) | Configure security and governance: the same controls plus dynamic data masking. It's part of "Implement and manage an analytics solution" (30–35%). |
| [Information Security Administrator Associate](https://learn.microsoft.com/credentials/certifications/information-security-administrator/) | [SC-401](https://learn.microsoft.com/credentials/certifications/resources/study-guides/sc-401) | Implement information protection; implement data loss prevention and retention; manage risks, alerts and activities (30–35% each). |

Purview remains the security and compliance layer. Only sensitivity labels, protection policies and DLP need Purview licensing; everything else works with a Fabric license. SC-401 tests that Purview work, which is why the plan adds it only for whoever owns labels and DLP.

All three are associate certifications. Renew each one every year, at no cost, by passing an online assessment on Learn before it expires ([certification renewal](https://learn.microsoft.com/credentials/certifications/renew-your-microsoft-certification)).

## Applied Skills

Learn lists no Applied Skill for Fabric governance or administration (checked 2026-11-27). Two come close:

- [Implement a Real-Time Intelligence solution with Microsoft Fabric](https://learn.microsoft.com/credentials/applied-skills/implement-a-real-time-intelligence-solution-with-microsoft-fabric/) matches the eventhouse and eventstream work in challenge 07.
- [Implement information protection and data loss prevention by using Microsoft Purview](https://learn.microsoft.com/credentials/applied-skills/implement-information-protection-and-data-loss-prevention-by-using-microsoft-purview/) overlaps the first two SC-401 skill areas.
