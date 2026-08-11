from faker.config import AVAILABLE_LOCALES

from simulator.utils.config_loader import load_countries


countries = load_countries()["countries"]


for country_code, country in countries.items():

    if "faker_locale" in country:
        locales = [country["faker_locale"]]
    else:
        locales = country["faker_locales"]

    for locale in locales:
        assert locale in AVAILABLE_LOCALES, (
            f"Unsupported Faker locale '{locale}' "
            f"configured for country '{country_code}'."
        )


print("All configured Faker locales are supported.")