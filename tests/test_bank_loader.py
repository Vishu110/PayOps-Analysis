from simulator.master_data.banks import generate_banks

from database.loaders.banks import load_banks


banks = generate_banks()

print(
    f"Generated {len(banks)} banks."
)

inserted_count = load_banks(banks)

print(
    f"Successfully inserted "
    f"{inserted_count} banks."
)

assert inserted_count == 12