# New Slicer Onboarding Change Map

| Step | File/module | Action | Mandatory | Agent automation | Evidence |
|---|---|---|---|---|---|
| Identifier/aliases | `slicers/<new>.py`, `contracts.py`, `registry.py` | define stable id; add aliases once | always | deterministic edit proposal | Feishu values and existing records |
| Format detection | processor + attachment use in `enrichment.py` | validate extension/media/encoding | always | inspect bytes/extensions | native samples |
| Parser | new processor | parse native structure | always | generate smoke skeleton | valid/invalid files |
| Inheritance | processor or documented preserve behavior | resolve only proven semantics | conditional | discover candidate fields | parent/child/cycle samples + confirmation |
| Canonicalization | processor | normalization, company policy, serializer | always | scaffold from contract | golden canonical artifact |
| Artifact | processor `serialize` | filename/media type/bytes | always | deterministic | exact filename/media expectation |
| Diff | processor `.diff` | categories, flattening, deterministic order | always | generate changed-field tests | semantic parameter catalog |
| Validation | processor methods | required fields, types, versions | always | structural checks | invalid fixtures |
| 3MF extractor | `three_mf/` adapter | inspect ZIP/XML/JSON/INI | conditional if 3MF used | list entries/keys | real 3MF |
| Parameter map | adapter/comparison core | native -> canonical mapping and units | conditional | candidate map only | paired values |
| Slot selection | comparison core/adapter | identity/index/duplicate rules | conditional | detect cardinality | multi-slot fixtures + confirmation |
| Consistency dispatch | `consistency_preview.py`, `consistency.py` | register validator and schema | conditional | completeness check | matching/mismatch pair |
| Feishu workflow | shared enrichment/preview/publication | verify no new branch needed | existing shared behavior | run integration tests | processor lookup and attachments |
| Fixtures | `tests/fixtures/slicers/<id>` | valid/invalid/inherited/3MF pairs | always for claimed support | inventory/generate manifest | source and expected values |
| Unit tests | `tests/test_<id>.py` | processor, diff, validation, aliases | always | skeleton generation | exact assertions |
| Integration tests | P9 preview/submit/publication | exercise lifecycle | always for production support | run/generate cases | Feishu fake contract |
| Documentation | support matrix and report | record capabilities/limits | always | generate matrix | accepted limitations |

Feishu and publication are existing shared behavior if the new processor satisfies the contract. Version backfill is conditional. A slicer is not complete until processor registration, consistency capability (if requested), fixtures and regression tests agree.
