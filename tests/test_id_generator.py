from simulator.utils.id_generator import generate_id


generated_ids = {
    generate_id("cus")
    for _ in range(10_000)
}

print(f"Generated IDs: {len(generated_ids)}")

assert len(generated_ids) == 10_000

print("All generated IDs are unique.")