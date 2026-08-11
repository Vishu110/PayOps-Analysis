from simulator.utils.config_loader import (
    load_countries,
    load_generator_config,
)


countries = load_countries()
generator_config = load_generator_config()

print("Countries:")
print(countries)

print("\nCustomer configuration:")
print(generator_config["customers"])