# P9-B1 Fixture Matrix

| Fixture | Type | Coverage | Status |
|---|---|---|---|
| downloads/legacy_preset_data_audit/recvgKBtHJUrDm_1_PPS100CF10 H2D.3mf | real Bambu Studio archive | 105 entries, project/model/slice/sequence, 1 filament slot, 13 thumbnail plates | verified extraction |
| test_three_mf.make_3mf | synthetic | project JSON, model XML, cardinality, PA, malformed/security harness | parser-only evidence |
| duplicate normalized archive names | synthetic security | duplicate path rejection | verified |

The real H2D fixture contains the four cooling fields: fan_min_speed=[0], fan_max_speed=[30], fan_cooling_layer_time=[20], and slow_down_layer_time=[6]. Real exported filament JSON samples contain the same four keys; for example PPS100CF10 H2C stores [20], [40], [40], and [8].
The real fixture contains no embedded filament/machine/process presets and no controlled before/after pair. It therefore cannot prove inheritance or save/reopen behavior. No real Bambu Studio versioned experiment is fabricated.

Missing real coverage:

- baseline versus one-field changes;
- inherited preset;
- project override pair;
- multiple filament slots;
- multiple plate types;
- unsliced/sliced pair;
- save/reopen/resave pair.
