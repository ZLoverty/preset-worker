# P9-B1 Resolution Rules

## Identity

filament_settings_id identifies project filament slots. Object and volume extruder metadata are 1-based slot references. They are not interchangeable with zero-based Python indexes or internal Bambu configuration indexes.

## Verified limited rules

1. A scalar project value is retained as STORED_ONLY and is not claimed to be filament-indexed.
2. A one-element array can be selected for a requested slot as configuration index 0.
3. An array whose length equals the number of filament slots can be selected by slot minus one.
4. Any other array cardinality is UNRESOLVED unless a future verified rule supplies the mapping.
5. Missing slot context returns UNRESOLVED for arrays.
6. Bambu printer pressure advance is NOT_APPLICABLE for runtime-effective interpretation.

## Cooling parameter mapping

The four cooling fields are:

- fan_min_speed: percentage, lower endpoint of part-cooling fan interpolation.
- fan_max_speed: percentage, upper endpoint and maximum part-cooling fan limit.
- fan_cooling_layer_time: seconds; Bambu source interpolates fan speed for layer times below this upper threshold.
- slow_down_layer_time: seconds; Bambu source uses this lower threshold to run at maximum fan speed for shorter layers and as the lower endpoint of interpolation.

The source relationship is in BambuStudio GCodeEditor.cpp: below slow_down_layer_time fan_max_speed is used; between slow_down_layer_time and fan_cooling_layer_time the fan is interpolated between fan_max_speed and fan_min_speed. These fields are extracted and resolved independently. One missing or ambiguous threshold must not be inferred from the other.

Real preset JSON and the H2D project both store all four using their exact names. The current resolver applies the same verified cardinality rule independently to each array and preserves the original seconds/percentage representation.

These rules intentionally do not implement the full Bambu get_filament_config_idx algorithm. The parser preserves raw arrays and reports missing context instead of guessing.

## Provenance

Every extracted priority parameter records entry, JSON path, raw value, scope, and resolution context. Resolved values additionally record configuration index and evidence.

## Known limitations

- No complete inheritance chain resolution.
- No runtime-effective claim without controlled slicing evidence.
- No inference from thumbnail count to plate count.
- No comparison with submitted preset JSON.
- No object-level print_flow_ratio conversion into filament flow.
