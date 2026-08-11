import secrets
import string


def generate_id(prefix: str, length: int = 24) -> str:
    """
    Generate a Stripe-style business identifier.

    Example:
        cus_8fK2mP9xLq7R3tYw5Nz1AaBc
    """

    if not prefix:
        raise ValueError("ID prefix cannot be empty.")

    if length <= 0:
        raise ValueError("ID length must be greater than zero.")

    characters = string.ascii_letters + string.digits

    suffix = "".join(
        secrets.choice(characters)
        for _ in range(length)
    )

    return f"{prefix}_{suffix}"