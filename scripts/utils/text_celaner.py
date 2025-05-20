import re


def clean_text(text: str) -> str:
    text_without_spaces = treat_formula(text)
    cleaned = (
        text_without_spaces.replace("$$", " ")
        .replace("$", " ")
        .replace("\\textrm{ }", "")
        .replace("\\left", "")
        .replace("\\right", "")
        .replace("\\leqslant", "\\leq")
    )
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.replace("\n", "").strip()


def treat_formula(text: str) -> str:
    pattern = re.compile(r"\$\$(.*?)\$\$|\$(.*?)\$", re.DOTALL)

    def replacer(match):
        formula = match.group(0)
        formula = basic_replaces(formula)
        formula = replace_underset(formula)
        formula = replace_operatorname(formula)
        formula = replace_math_bold(formula)
        formula = replace_vectors(formula)
        formula = replace_superscripts(formula)
        formula = remove_unnecessary_parentheses(formula)
        formula = remove_unnecessary_dots(formula)
        formula = treat_angles(formula)
        formula = remove_special_characters(formula)
        formula = replace_angles(formula)
        formula = treat_primes(formula)
        formula = replace_mathrm(formula)
        formula = replace_text(formula)
        formula = replace_overs(formula)
        formula = replace_integrals(formula)
        return formula

    return pattern.sub(replacer, text)


def basic_replaces(text: str) -> str:
    return (
        text.replace(" ", "")
        .replace("\\textrm{}", "")
        .replace("\\left", "")
        .replace("\\right", "")
        .replace("\\quad", "")
        .replace("\\leqslant", "\\leq")
        .replace("|", "\\mid")
        .replace("\\\\", "")
        .replace("\n", "")
        .strip()
    )


def replace_underset(text: str) -> str:
    pattern = re.compile(r"\\underset{([^}]+)}{([^}]+)}", re.DOTALL)
    return pattern.sub(
        lambda m: (
            f"\\{m.group(2)}_{{{m.group(1)}}}"
            if m.group(2) == "lim"
            else f"\\underset{{{m.group(1)}}}{m.group(2)}"
        ),
        text,
    )


def replace_operatorname(text: str) -> str:
    return re.sub(r"\\operatorname{([^}]+)}", r"\1", text)


def replace_math_bold(text: str) -> str:
    return re.sub(
        r"\\(mathbf|boldsymbol|bm|mathbb|mathsf|mathit){([^}]+)}", r"\2", text
    )


def replace_vectors(text: str) -> str:
    return re.sub(r"\\vec{([^}]+)}", r"\1", text)


def replace_superscripts(text: str) -> str:
    return re.sub(r"\^\{([^}]+)}", r"^\1", text)


def remove_unnecessary_parentheses(text: str) -> str:
    text = re.sub(r"\(\(([^()]+)\)\)", r"(\1)", text)
    return re.sub(r"\b(\w+)\((\w+)\)", r"\1\2", text)


def remove_unnecessary_dots(text: str) -> str:
    text = re.sub(r"(?<!\d)\.|\.(?!\d)", "", text)
    return text.replace("\\cdot", "")


def treat_angles(text: str) -> str:
    return (
        text.replace("sin", "sen")
        .replace("\\sen", "sen")
        .replace("\\cos", "cos")
        .replace("\\tan", "tg")
        .replace("\\sec", "sec")
        .replace("\\csc", "csc")
        .replace("\\cot", "cot")
    )


def remove_special_characters(text: str) -> str:
    return re.sub(r"[\u2000-\u206F\uFEFF]", "", text)


def replace_angles(text: str) -> str:
    return text.replace("〈", "\\langle").replace("〉", "\\rangle")


def treat_primes(text: str) -> str:
    return re.sub(r"\\prime|'", "'", text)


def replace_mathrm(text: str) -> str:
    return re.sub(r"\\mathrm{(?:~)?(\w+)}", r"\1", text)


def replace_text(text: str) -> str:
    return re.sub(r"\\text{([^}]*)}", r"\1", text)


def replace_overs(text: str) -> str:
    text = re.sub(r"\\overline{([^}]*)}", r"\1", text)
    text = re.sub(r"\\overset{[^}]*}{([^}]*)}", r"\1", text)
    text = re.sub(r"\\overrightarrow{([^}]*)}", r"\1", text)
    text = re.sub(r"\\hat{([^}]*)}", r"\1", text)
    return text


def replace_integrals(text: str) -> str:
    # Aqui pode adicionar lógica adicional se necessário
    return text
