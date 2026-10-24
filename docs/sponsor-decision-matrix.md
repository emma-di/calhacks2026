# Sponsor choices when building

**Policy:** whenever we need storage, an API, backend, hosting, auth or another technical component,
compare a sponsor substitute first. Prefer it when it serves the real feature with little loss or
extra complexity and the reward is worthwhile. Do not invent features or pivot domains for a prize.
Cash, useful hardware and strategic access count differently from credits; credit face value is
not cash. Unknown rewards remain unknown. There is no fixed dollar or setup-time threshold.

**Source [S1]:** user-supplied text snapshot of **“Cal hacks 13.0 / prizes,” “Updated Oct 23, 9:55 PM”**
(October 23, 2026). All listed rewards and track conditions below are attributed to that snapshot;
they have **not been independently revalidated**. No source-page URL was supplied, so none is
invented here. Links embedded in that snapshot are leads, not proof of current eligibility.
Recommendations are project judgments, not adoption or infrastructure provisioning.

## Decisions against actual product needs

| Actual need | Candidate / listed reward [S1] | Minimal meaningful use | Decision |
| --- | --- | --- | --- |
| Build and test onboarding/companion faster | **Mana — $5,000 cash** | Use a real prototype or build/debug session that changes the shipped flow; retain evidence. | **Strong fit; pursue useful work.** Submission needs one or two public Mana pages/chats and a demo moment showing its contribution. Hosting inside Mana is a bonus, not a requirement. Export/live relay remain unproven; preserve the local app. |
| Persist preferences and synchronize a companion/mirror across clients | **Convex — $5,000 cash** | Save real profiles and subscribe to actual shared alert/session state. | **Recommended next persistence/sync candidate; not adopted.** Prove one end-to-end flow and local fallback before migration. Cloud availability must not gate local urgent alerts. |
| Same shared real-time backend need | **Spacetime — listed main prizes $2,048 / $1,024 / $512** | Make it the real shared-state backend, not an unused side database. | **Alternative to Convex; choose one.** Compare setup and sync behavior; do not stack equivalent state layers. Snapshot lists a separate Scrabblebot tournament; do not count its awards for this product. |
| Transcribe speech to detect a configured name | **Cartesia — Meta glasses, still TBD** | Evaluate its actual speech-to-text capability in the name worker, with measured names/negative cases. | **Evaluate capability and qualification.** Snapshot asks for a useful voice experience with voice core to the product; STT-only use is not automatically qualifying. Confirm with the sponsor. No unnecessary spoken output. |
| Optional free-text setup preferences | **Anthropic / Claude — reward “Coming soon!”** | Convert a user's intent into proposed settings for explicit review, with schema validation and ordinary forms as fallback. | **Optional after ordinary settings work.** Reward unknown; do not chase it purely for a prize. Snapshot requires a named community, real problem and thoughtful meaningful Claude use. Validate users; do not claim research we have not done. |
| Demonstrate AI helping people notice one another | **Meta — Round 2 invitation, travel/accommodation, swag** | Working wearer/audience demo of name/important-sound awareness and human connection. | **Strong product fit; pursue the submission story.** Advancement is subject to eligibility and Round 2 rules; owning a Meta headset is not stated as the requirement. Strategic access, not cash. |
| Environmental classification and local alert delivery | No suitable sponsor replacement established in [S1] | Keep measured pretrained recognition and deterministic local priority/display paths. | **Keep current implementation.** A sponsor LLM must not decide urgent-alert tiers or sit in their delivery path. |
| Hosting, login or alternative database, only if genuinely needed | Vultr: Tab5; DigitalOcean: mouse; Auth0: headphones; MongoDB Atlas: IoT kit; Tiger Data: Stream Deck Mini | Use a needed service in the running product. | **Defer until a real need exists.** Small prizes/credits do not justify extra infrastructure or a second database beside the selected state layer. |
| Existing design/build documentation | Figma: gift cards + recruiting session; Notability: Pro year + merch | Use the tool substantively in actual design/notes, meeting its track rules. | **Low-overhead opportunities only.** Do not rebuild finished screens or create retrospective fake evidence. |

## Do not distort the build for these tracks

| Candidate / reward in [S1] | Why we defer or skip |
| --- | --- |
| Factory: **$2,000 cash**, credits, swag | Requires the **Droid SDK doing real work in the running product**. Using a coding assistant does not satisfy that condition. No current product need for that runtime agent. |
| Hyphenate: **$8,000 / $5,000 / $3,000 cash**, interviews | Finance/autonomous-enterprise domain; wrong product. Do not pivot despite the larger amounts. |
| Capital One / CRS / Coinbase / Visa / Solana | Financial data, payments, commerce or transactions are not needed by these glasses. Rewards do not make them useful integrations. |
| Apify: $5,000 distributed prize pool; Bright Data: credits + gift cards | No core public-web data need. Adding scraping would add a separate product feature just to qualify. |
| CREAO | “2500” and “1500” have **no currency/type specified** in the snapshot; do not label them cash. A separate entry explicitly lists $1,000 total cash across tracks, plus Launchpad benefits. Requirements and fit still need review. |
| Gemini / other MLH extras, voice generation, biometrics, agent memory | Swag, hardware or credits are optional benefits when an already-needed feature fits. Do not add a chatbot, synthetic speech, camera sensing or memory system solely for eligibility. |

## Small decision record before adoption

For each real technical choice, record: **need → sponsor vs baseline → listed reward/type and verified
eligibility → product benefit → setup cost → integration risk → local/offline fallback → adopt/defer
and owner → working-demo evidence**. Include privacy, network dependence and secret handling where relevant.
Preserve recognizer/priority/display contracts; show judges the sponsor's actual contribution and
limitations. Recheck official rules, reward terms and submission requirements before claiming eligibility.

This matrix supplements the [sponsor build guide](sponsor-build-guide.md), not the
[master product TODO](../TODO.md). No service has been provisioned by writing this document.
