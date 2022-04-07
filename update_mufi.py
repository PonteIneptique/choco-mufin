import json

with open("original_mufi_json.json") as inp, open("chocomufin/mufi.json", "w") as out:
    out_dict = {}
    for line in json.load(inp):
        out_dict[line["codepoint"]] = {"description": line["description"], "deprecated": line["deprecated"]}
    json.dump(out_dict, out)
