from simulator.master_data.processors import (
    generate_processors,
)

from database.loaders.processors import (
    load_processors,
)


processors = generate_processors()

print(
    f"Generated {len(processors)} processors."
)

inserted_count = load_processors(
    processors
)

print(
    f"Successfully inserted "
    f"{inserted_count} processors."
)

assert inserted_count == 5