import json
import os
import matplotlib.pyplot as plt

with open('../data/dataset_snopes.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

root_dir = "plot_output_snopes"
os.makedirs(root_dir, exist_ok=True) 

label_map = {
    "True": "True",
    "Mostly True": "True",
    "Half True": "Mixed",       # in case 'Half True' is used
    "Mostly False": "Mixed",
    "False": "False",
    "Pants on Fire": "False"        # mapped to "False"
}
# label_map = {
#     "True": "True",
#     "Mostly True": "True",
#     "Mostly False": "False",
#     "False": "False",
# }
new_labels = list(set(label_map.values()))

# Group metrics by the *aggregated* labels
grouped_metrics = {label: {
        "credibility_scores": [],
        "domain_ages": [],
        "bias_scores": [],
        "tld_scores": [],
        "page_ranks": [],
        "factual_scores": []
    } for label in new_labels}

for claim_obj in data:
    # Get the mapped label.  Crucially, use .get() with a default
    # value to handle cases where the label might not be in the map.
    mapped_label = label_map.get(claim_obj["label"], None)
    if mapped_label is None:
        print(f"Warning: Unknown label '{claim_obj['label']}'")
        continue  # Skip this data point

    grouped_metrics[mapped_label]["credibility_scores"].append(claim_obj["domain_authority_metrics"]["credibility_rating_score"])
    grouped_metrics[mapped_label]["domain_ages"].append(claim_obj["domain_authority_metrics"]["domain_age"])
    grouped_metrics[mapped_label]["bias_scores"].append(claim_obj["domain_authority_metrics"]["bias_rating_score"])
    grouped_metrics[mapped_label]["tld_scores"].append(claim_obj["domain_authority_metrics"]["tld_score"])
    grouped_metrics[mapped_label]["page_ranks"].append(claim_obj["domain_authority_metrics"]["page_rank"])
    grouped_metrics[mapped_label]["factual_scores"].append(claim_obj["domain_authority_metrics"]["factual_rating_score"])

# -----------------------------------------------------------
# CREDIBILITY SCORE HISTOGRAM
credibility_labels = {
    0: 'cannot be determined',
    1: 'low credibility',
    2: 'mixed credibility',
    3: 'medium credibility',
    4: 'high credibility'
}
for label in new_labels:
    scores = [x if x is not None else 0 for x in grouped_metrics[label]["credibility_scores"]]
    plt.figure() 
    plt.xlabel(f"Credibility Score ({label})")
    plt.ylabel("Frequency")
    plt.hist(scores, bins=len(credibility_labels), align='left', color='skyblue', edgecolor='black')
    plt.xticks(range(len(credibility_labels)), list(credibility_labels.values()), rotation=45, ha='right')
    plt.tight_layout()
    
    # Save the plot
    label_dir = os.path.join(root_dir, label)  # Create subdirectory for the label
    os.makedirs(label_dir, exist_ok=True)  # Create label directory if it doesn't exist
    filename = os.path.join(label_dir, "credibility_scores.png")
    plt.savefig(filename)
    plt.close() # close figure

# -----------------------------------------------------------
# DOMAIN AGE HISTOGRAM
for label in new_labels:
    domain_ages = [x for x in grouped_metrics[label]["domain_ages"] if x is not None]
    if not domain_ages:  # Handle empty lists
        print(f"No domain age data for label: {label}")
        continue
    plt.figure()
    plt.xlabel(f"Domain Age ({label})")
    plt.ylabel("Frequency")
    plt.hist(domain_ages, color='skyblue', edgecolor='black')

    # Save the plot
    label_dir = os.path.join(root_dir, label)
    os.makedirs(label_dir, exist_ok=True)
    filename = os.path.join(label_dir, "domain_ages.png")
    plt.savefig(filename)
    plt.close()

# -----------------------------------------------------------
# Bias Scores, per label
bias_labels = {
    0: "cannot be determined",
    1: "left",
    2: "leftcenter",
    3: "center/pro-science",
    4: "right-center",
    5: "right/consp/fnews",
}
for label in new_labels:
    bias_scores = [x if x is not None else 0 for x in grouped_metrics[label]["bias_scores"]]
    plt.figure()
    plt.xlabel(f"Bias Score ({label})")
    plt.ylabel("Frequency")
    plt.hist(bias_scores, bins=len(bias_labels), align='left', color='skyblue', edgecolor='black')
    plt.xticks(range(len(bias_labels)), list(bias_labels.values()), rotation=45, ha='right')
    plt.tight_layout()

    # Save the plot
    label_dir = os.path.join(root_dir, label)
    os.makedirs(label_dir, exist_ok=True)
    filename = os.path.join(label_dir, "bias_scores.png")
    plt.savefig(filename)
    plt.close()

# -----------------------------------------------------------
# Factual Scores, per label
factual_labels = {
    0: "cannot be determined",
    1: "very low",
    2: "low",
    3: "mixed",
    4: "mostly factual",
    5: "high",
    6: "very high",
}
for label in new_labels:
    factual_scores = [x if x is not None else 0 for x in grouped_metrics[label]["factual_scores"]]
    plt.figure()
    plt.xlabel(f"Factual Score ({label})")
    plt.ylabel("Frequency")
    plt.hist(factual_scores, bins=len(factual_labels), align='left', color='skyblue', edgecolor='black')
    plt.xticks(range(len(factual_labels)), list(factual_labels.values()), rotation=45, ha='right')
    plt.tight_layout()
    
    # Save the plot
    label_dir = os.path.join(root_dir, label)
    os.makedirs(label_dir, exist_ok=True)
    filename = os.path.join(label_dir, "factual_scores.png")
    plt.savefig(filename)
    plt.close()

# -----------------------------------------------------------
# Page Ranks, per label
for label in new_labels:
    page_ranks = [x for x in grouped_metrics[label]["page_ranks"] if x is not None]
    if not page_ranks:
        print(f"No page rank data for label: {label}")
        continue
    plt.figure()
    plt.xlabel(f"Page Rank ({label})")
    plt.ylabel("Frequency")
    plt.hist(page_ranks, color='skyblue', edgecolor='black')

    # Save the plot
    label_dir = os.path.join(root_dir, label)
    os.makedirs(label_dir, exist_ok=True)
    filename = os.path.join(label_dir, "page_ranks.png")
    plt.savefig(filename)
    plt.close()

# -----------------------------------------------------------
# TLD Scores, per label
for label in new_labels:
    tld_scores = [x for x in grouped_metrics[label]["tld_scores"] if x is not None]
    if not tld_scores:
        print(f"No TLD score data for label: {label}")
        continue
    plt.figure()
    plt.xlabel(f"TLD Score ({label})")
    plt.ylabel("Frequency")
    plt.hist(tld_scores, color='skyblue', edgecolor='black')

    # Save the plot
    label_dir = os.path.join(root_dir, label)
    os.makedirs(label_dir, exist_ok=True)
    filename = os.path.join(label_dir, "tld_scores.png")
    plt.savefig(filename)
    plt.close()