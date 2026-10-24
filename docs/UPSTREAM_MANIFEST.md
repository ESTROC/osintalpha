# Upstream project adoption inventory (October 2026)

**No upstream repository has been wholesale copied into this source package.** Names appear in the project library as launchable references. Real integrated data comes from explicit adapters calling original APIs. Copying an upstream application's UI or crawler is deferred until legal/data/security review.

| System | Code / expected license | Role | Current state | What must be audited before incorporation |
|---|---|---|---|---|
| [OSIRIS](https://github.com/simplifaisoul/osiris) | MIT | Camera/geo adapters, viewport fetching | Launcher/reference | Individual publisher rights, errors and caching, dependency scans |
| [God's Eye View](https://github.com/bilawalsidhu/gods-eye-view) | MIT code, mixed bundled data | 3D geographic viewer | Launcher/reference | Third-party assets, noncommercial sources, rendering/billing |
| [World Monitor](https://github.com/koala73/worldmonitor) | AGPL-3.0 core; some MIT SDK clients | Event intelligence | Launcher/reference | AGPL compliance or commercial source license, hosted API EULA |
| [Argus](https://github.com/GoSlowPoke168/Argus) | MIT | Camera ingestion and catalog | Launcher/reference | Camera publisher terms, scraper fragility, lack of test coverage |
| [CamForge](https://github.com/SoCloseSociety/camforge) | MIT | Public camera policies/relay | Launcher/reference | MediaMTX control exposure, missing redaction implementation, permissions |
| [SpiderFoot](https://github.com/smicallef/spiderfoot) | MIT | OSINT collectors | Launcher/reference | Approved modules, network scope, dependency isolation and licensing |
| [Maigret](https://github.com/soxoj/maigret) | MIT (verify current version) | Username lead discovery | Disabled | Name-collision false positives, provider access/ToS |
| [Sherlock](https://github.com/sherlock-project/sherlock) | MIT (verify current version) | Username candidates | Disabled | Site response heuristics, ToS, candidate verification |
| [OpenAleph](https://github.com/openaleph/openaleph) | Multi-component review | Evidence/document engine | Launcher/reference | Heavy infra, API semantics, component licenses |
| [FollowTheMoney](https://github.com/opensanctions/followthemoney) | MIT | Entity schema | Reference | Data migration and provenance schema |
| [ArchiveBox](https://github.com/ArchiveBox/ArchiveBox) | MIT (verify commit) | Authorized archiving | Reference | WARC/storage, source rights and deletion |
| [pywb](https://github.com/webrecorder/pywb) | Apache-2.0 | WARC replay | Reference | Archive access control |
| [Dedupe](https://github.com/dedupeio/dedupe) | MIT | Candidate ranking | Reference | Benchmark, confidence calibration, human confirmation |
| [IntelOwl](https://github.com/intelowlproject/IntelOwl) | Check AGPL/version | Threat intelligence | Disabled | License, module outbound effects, malware sandbox |
| [OpenCTI](https://github.com/OpenCTI-Platform/opencti) | Apache-2.0 community core | Threat graph | Reference | Hosting complexity, connectors and licensing |
| [NASA Worldview](https://github.com/nasa-gibs/worldview) | Mixed app/data terms | Satellite layer | Launcher | Imagery capture date, API quota, attribution |
| [Copernicus Browser](https://browser.dataspace.copernicus.eu/) | Service/data specific | Sentinel imagery | Launcher | API quotas, license and imagery spatial resolution |
| [Bellingcat Toolkit](https://github.com/bellingcat/toolkit) | Per-tool | OSINT method directory | Launcher | Vet each linked tool independently |

## Official APIs wired into our original code

- GitHub public user search
- OpenAlex author search
- Crossref publication metadata
- GLEIF public entity search
- Wikipedia and Wikidata candidate search
- GDELT article discovery
- USGS earthquake feed
- NASA EONET environmental observations
- Caltrans public road-camera metadata
- Optional TfL JamCam API (registered developer key)

All are best-effort connectors. The build container cannot resolve external DNS; current live availability and output correctness still require deployment-network smoke tests. External source rights must be checked at launch.
