# V7.1 — Explainable public-identity candidate comparison

### New capabilities
- Candidate-source comparison displays two public profiles side by side with published names, organizations, locations, handles and public sites.
- It labels matched attributes, differences and attributes not published by both sources.
- Ranks candidate records against known public case clues (city, organization, public handle) and explains matched, missing or different fields.
- Generates up to 40 **review suggestions** when public usernames or website identifiers overlap across different providers; no automatic account merge or verified-person claim.
- Rejected evidence records are excluded from suggested links.
- The UI and API enforce case ownership and require both compared sources to belong to the same case.
- Synthetic regression cases cover distinct same-name academics/developers, shared handles, missing and different attributes, rejected records and cross-case access.

### Important limitations
The system does **not** infer that matching usernames represent the same real-world person. Shared employer or location is circumstantial. Different published locations/employers may reflect changes over time, not distinct people. No calibrated identity probability, independent possession verification, complete cross-platform discovery or ground-truth benchmark is provided.

This change should be considered a useful analyst comparison tool, **not** a completed identity-resolution engine. Users must verify identity associations independently before making consequential assertions.
