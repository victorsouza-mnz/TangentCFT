import json
import pandas as pd
import re


with open("./app/assert/test_results.json", "r") as f:
    data = json.load(f)

algorithm_map = {
    "search-pure-text": "Texto Puro",
    "search-text-with-treated-formulas": "Fórmulas Tratadas",
    "search-text-vector": "Embedding Texto",
    "search-with-text-without-formula-combined-with-slt-formula-vector#approach_1": "Híbrido #1",
    "search-with-text-without-formula-combined-with-slt-formula-vector#approach_2": "Híbrido #2",
    "search-with-text-without-formula-combined-with-slt-formula-vector#approach_3": "Híbrido #3",
    "search-with-text-without-formula-combined-with-slt-formula-vector#approach_4": "Híbrido #4",
}

rows = []

# itera sobre cada algoritmo de busca
for algorithm, tests in data["performance_summary"].items():
    # itera sobre cada tipo de query
    for test_type, metrics in tests.items():
        base_test = re.sub(r"_truncated_50$", "", test_type)
        is_truncated = "truncated" in test_type

        row = {
            "Algoritmo": algorithm_map.get(algorithm, algorithm),
            "Modificação": test_type,
            "Modificação_Base": base_test,
            "Total_Cases": metrics["total_cases"],
            "Successful_Requests": metrics["successful_requests"],
            "Success_Rate_Percent": metrics["success_rate_percent"],
            "Found_in_Top_K": metrics["found_in_top_k"],
            "Hit_Rate_Percent": metrics["hit_rate_percent"],
            "Avg_Response_Time_Seconds": metrics["avg_response_time_seconds"],
            "Avg_Position_When_Found": metrics["avg_position_when_found"],
            "All_Positions": metrics["all_positions"],
            "Median_Position": metrics["median_position"],
            "Is_Truncated": is_truncated,
        }
        rows.append(row)

df = pd.DataFrame(rows)

df.to_csv("./app/assert/resultados_experimento.csv", index=False)
print("DataFrame criado com sucesso!")
print(f"Total de registros: {len(df)}")
print(df.head())
