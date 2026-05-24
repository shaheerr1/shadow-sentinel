from transformers import pipeline

def load_models():
    print("Loading Model A...")
    model_a = pipeline(
        "sentiment-analysis",
        model="distilbert-base-uncased-finetuned-sst-2-english"
    )

    print("Loading Model B...")
    model_b = pipeline(
    "sentiment-analysis",
    model="siebert/sentiment-roberta-large-english"
    )

    print("Both models loaded.")
    return model_a, model_b

if __name__ == "__main__":
    model_a, model_b = load_models()

    test_inputs = [
        "This is absolutely amazing!",
        "I can't believe how bad this was",
        "meh it was whatever lol",
        "not bad but not great either",
        "this slaps ngl"
    ]

    print("\n--- Prediction Comparison ---")
    for text in test_inputs:
        a = model_a(text)[0]
        b = model_b(text)[0]
        match = "✅" if a['label'].lower() in b['label'].lower() else "❌"
        print(f"{match} Input: {text}")
        print(f"   Model A: {a['label']} ({a['score']:.2f})")
        print(f"   Model B: {b['label']} ({b['score']:.2f})")
        print()