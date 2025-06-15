import re

# TODO : remover informação de italic ex na formula id: 63811


# Função principal que limpa o texto, removendo espaços extras e processando fórmulas matemáticas
# Input: "Considere a equação $x^2 + y^2 = r^2$ do círculo."
# Output: "Considere a equação x^2+y^2=r^2 do círculo."
def clean_text(text: str) -> str:
    text_without_spaces = treat_formula(text)
    cleaned = (
        text_without_spaces.replace(
            "$$", " "
        )  # Remove delimitadores de equação em bloco
        .replace("$", " ")  # Remove delimitadores de equação inline
        .replace("\\textrm{ }", "")  # Remove comandos de texto vazios
        .replace("\\left", "")  # Remove comando \left para parênteses
        .replace("\\right", "")  # Remove comando \right para parênteses
        .replace("\\leqslant", "\\leq")  # Padroniza símbolo de menor ou igual
    )
    # Substitui múltiplos espaços por um único espaço
    # Ex: "a   b  c" -> "a b c"
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.replace("\n", "").strip()


# Processa fórmulas matemáticas no texto, aplicando várias transformações
# Input: "A área do círculo é $A = \pi r^2$"
# Output: "A área do círculo é A=πr^2"
def treat_formula(text: str) -> str:
    # Padrão para capturar expressões matemáticas entre $$ ou $
    # Ex: "$x+y$" ou "$$\int f(x) dx$$"
    pattern = re.compile(
        r"(\$\$[\s\S]*?\$\$"  # $$...$$
        r"|\$[^\n]*?\$"  # $...$
        r"|\\\[.*?\\\]"  # \[...\]
        r"|\\begin\{.*?\}[\s\S]*?\\end\{.*?\})",  # \begin{...}...\end{...}
        re.MULTILINE,
    )

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


# Faz substituições básicas em fórmulas LaTeX, removendo espaços e comandos desnecessários
# Input: "$\left( x + y \right) \quad \leqslant \textrm{} z$"
# Output: "$(x+y)\\leq z$"
def basic_replaces(text: str) -> str:
    return (
        text.replace(" ", "")  # Remove espaços em branco
        .replace("\\textrm{}", "")  # Remove comandos de texto vazios
        .replace("\\left", "")  # Remove comando \left para parênteses
        .replace("\\right", "")  # Remove comando \right para parênteses
        .replace("\\quad", "")  # Remove comando \quad para espaço
        .replace("\\leqslant", "\\leq")  # Padroniza símbolo de menor ou igual
        .replace("|", "\\mid")  # Padroniza símbolo de barra vertical
        .replace("\\\\", "")  # Remove comando \\ para quebra de linha
        .replace("\n", "")  # Remove quebras de linha
        .strip()  # Remove espaços em branco extras
    )


# Trata o comando \underset do LaTeX, com tratamento especial para limites
# Input: "$\underset{x \to 0}{lim} f(x)$"
# Output: "$\lim_{x \to 0} f(x)$"
# Input: "$\underset{i=1}{n}$" (caso não seja um limite)
# Output: "$\underset{i=1}{n}$" (mantém como estava)
def replace_underset(text: str) -> str:
    # Captura o conteúdo dentro dos dois conjuntos de chaves do \underset
    pattern = re.compile(r"\\underset{([^}]+)}{([^}]+)}", re.DOTALL)
    return pattern.sub(
        lambda m: (
            # Se o segundo grupo for "lim", reformata como \lim_{...}
            f"\\{m.group(2)}_{{{m.group(1)}}}"
            if m.group(2) == "lim"
            else f"\\underset{{{m.group(1)}}}{m.group(2)}"
        ),
        text,
    )


# Remove o comando \operatorname do LaTeX
# Input: "$\operatorname{sen}(x)$"
# Output: "$sen(x)$"
def replace_operatorname(text: str) -> str:
    # Captura o conteúdo dentro das chaves do \operatorname
    return re.sub(r"\\operatorname{([^}]+)}", r"\1", text)


# Remove comandos de formatação matemática (negrito, blackboard, sans-serif, itálico)
# Input: "$\mathbf{v} + \mathbb{R} + \mathsf{T} + \mathit{x}$"
# Output: "$v + R + T + x$"
def replace_math_bold(text: str) -> str:
    # Captura qualquer um dos comandos de formatação e seu conteúdo
    return re.sub(
        r"\\(mathbf|boldsymbol|bm|mathbb|mathsf|mathit){([^}]+)}", r"\2", text
    )


# Remove a notação de vetor do LaTeX
# Input: "$\vec{v} \cdot \vec{u}$"
# Output: "$v \cdot u$"
def replace_vectors(text: str) -> str:
    # Captura o conteúdo dentro das chaves do \vec
    return re.sub(r"\\vec{([^}]+)}", r"\1", text)


# Simplifica a notação de superescrito
# Input: "$x^{2+3}$"
# Output: "$x^2+3$"
def replace_superscripts(text: str) -> str:
    # Captura o conteúdo dentro das chaves após o símbolo ^
    return re.sub(r"\^\{([^}]+)}", r"^\1", text)


# Remove parênteses redundantes
# Input: "$((x+y))$" e "$f(x)$"
# Output: "$(x+y)$" e "$fx$"
def remove_unnecessary_parentheses(text: str) -> str:
    # Remove parênteses duplos
    # Ex: "((x+y))" -> "(x+y)"
    text = re.sub(r"\(\(([^()]+)\)\)", r"(\1)", text)
    # Remove parênteses entre identificadores
    # Ex: "f(x)" -> "fx"
    return re.sub(r"\b(\w+)\((\w+)\)", r"\1\2", text)


# Remove pontos desnecessários e o comando \cdot
# Input: "$a.b \cdot c.$"
# Output: "$ab c$"
def remove_unnecessary_dots(text: str) -> str:
    # Remove pontos que não estão entre dígitos
    # Ex: "a." -> "a", ".b" -> "b"
    text = re.sub(r"(?<!\d)\.|\.(?!\d)", "", text)
    # Remove o operador de multiplicação \cdot
    # Ex: "a \cdot b" -> "a b"
    return text.replace("\\cdot", "")


# Padroniza a notação de funções trigonométricas
# Input: "$sin(x) + \cos(y) + \tan(z)$"
# Output: "$sen(x) + cos(y) + tg(z)$"
def treat_angles(text: str) -> str:
    return (
        text.replace("sin", "sen")  # Substitui sin por sen
        .replace("\\sen", "sen")  # Substitui \sen por sen
        .replace("\\cos", "cos")  # Substitui \cos por cos
        .replace("\\tan", "tg")  # Substitui \tan por tg
        .replace("\\sec", "sec")  # Substitui \sec por sec
        .replace("\\csc", "csc")  # Substitui \csc por csc
        .replace("\\cot", "cot")  # Substitui \cot por cot
    )


# Remove caracteres Unicode especiais
# Input: "$x​y$" (com um caractere invisível Unicode entre x e y)
# Output: "$xy$"
def remove_special_characters(text: str) -> str:
    # Remove caracteres de formatação Unicode e byte order mark
    # Faixa \u2000-\u206F inclui espaços, traços e caracteres especiais
    return re.sub(r"[\u2000-\u206F\uFEFF]", "", text)


# Substitui colchetes angulares Unicode por sua notação LaTeX
# Input: "$〈v, w〉$" (usando caracteres Unicode)
# Output: "$\langle v, w\rangle$"
def replace_angles(text: str) -> str:
    return text.replace("〈", "\\langle").replace("〉", "\\rangle")


# Padroniza a notação de símbolos prime (linha)
# Input: "$f^{\prime} + g'$"
# Output: "$f' + g'$"
def treat_primes(text: str) -> str:
    # Substitui o comando \prime ou o caractere ' por '
    return re.sub(r"\\prime|'", "'", text)


# Remove o comando \mathrm do LaTeX
# Input: "$\mathrm{kg} + \mathrm{~m}$"
# Output: "$kg + m$"
def replace_mathrm(text: str) -> str:
    # Captura o conteúdo dentro do \mathrm, permitindo um ~ opcional
    return re.sub(r"\\mathrm{(?:~)?(\w+)}", r"\1", text)


# Remove o comando \text do LaTeX
# Input: "$x + \text{valor}$"
# Output: "$x + valor$"
def replace_text(text: str) -> str:
    # Captura o conteúdo dentro do \text
    return re.sub(r"\\text{([^}]*)}", r"\1", text)


# Remove comandos overline, overset, overrightarrow e hat
# Input: "$\overline{AB} + \overset{*}{x} + \overrightarrow{PQ} + \hat{v}$"
# Output: "$AB + x + PQ + v$"
def replace_overs(text: str) -> str:
    text = re.sub(r"\\overline{([^}]*)}", r"\1", text)
    text = re.sub(r"\\overset{[^}]*}{([^}]*)}", r"\1", text)
    text = re.sub(r"\\overrightarrow{([^}]*)}", r"\1", text)
    text = re.sub(r"\\hat{([^}]*)}", r"\1", text)
    return text


# Função para tratar integrais, padronizando notações de integrais simples, duplas e triplas
# Input: "$\int_a^b f(x) dx + (\int) g(x) dx + \int\int h(x,y) dxdy + \int\int\int j(x,y,z) dxdydz$"
# Output: "$\int_a^b f(x) dx + \int g(x) dx + \iint h(x,y) dxdy + \iiint j(x,y,z) dxdydz$"
def replace_integrals(text: str) -> str:
    if "int" not in text:
        return text

    text = text.replace(
        "(\\int)", "\\int"
    )  # Remove parênteses desnecessários de integrais simples
    text = text.replace(
        "(\\iint)", "\\iint"
    )  # Remove parênteses desnecessários de integrais duplas
    text = text.replace(
        "(\\iiint)", "\\iiint"
    )  # Remove parênteses desnecessários de integrais triplas
    text = text.replace("int_", "int")  # Remove operador desnecessário após integral
    text = text.replace("\\int\\int\\int", "\\iiint")  # Padroniza integrais triplas
    text = text.replace("\\int\\int", "\\iint")  # Padroniza integrais duplas

    return text
