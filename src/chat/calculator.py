import ast
import math
import operator

MAX_EXPRESSION_LENGTH = 300

_BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPERATORS = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_FUNCTIONS = {
    'sqrt': math.sqrt,
    'log': math.log,
    'log10': math.log10,
    'exp': math.exp,
    'abs': abs,
    'min': min,
    'max': max,
    'round': lambda value, digits=0: round(value, int(digits)),
}
_CONSTANTS = {'pi': math.pi, 'e': math.e}


def evaluate(expression: str) -> float:
    """
    Evaluates an arithmetic expression written by the model. Raises ValueError when it is not valid.

    WARNING: never replace this with eval(). The expression comes from the model and is steered by user text,
    so only the nodes handled in _evaluate may run.
    """
    if len(expression) > MAX_EXPRESSION_LENGTH:
        raise ValueError(f'expressão maior que {MAX_EXPRESSION_LENGTH} caracteres')
    try:
        tree = ast.parse(expression.strip(), mode='eval')
    except SyntaxError:
        raise ValueError('expressão inválida, use apenas números, + - * / ** e funções como sqrt(x)')
    try:
        result = _evaluate(tree.body)
    except ZeroDivisionError:
        raise ValueError('divisão por zero')
    except OverflowError:
        raise ValueError('resultado grande demais')
    except (TypeError, RecursionError):
        raise ValueError('expressão inválida')
    if isinstance(result, complex) or math.isnan(result):
        raise ValueError('a expressão não tem resultado real')
    return result


def _evaluate(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        # floats keep a huge power like 9**9**9 from hanging: it overflows instead of building a giant int
        return float(node.value)
    if isinstance(node, ast.Name) and node.id in _CONSTANTS:
        return _CONSTANTS[node.id]
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPERATORS:
        return _BINARY_OPERATORS[type(node.op)](_evaluate(node.left), _evaluate(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPERATORS:
        return _UNARY_OPERATORS[type(node.op)](_evaluate(node.operand))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _FUNCTIONS:
        if node.keywords:
            raise ValueError('funções aceitam apenas argumentos posicionais')
        args = [_evaluate(arg) for arg in node.args]
        try:
            return _FUNCTIONS[node.func.id](*args)
        except ValueError:
            raise ValueError(f'argumento inválido para {node.func.id}')
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitXor):
        raise ValueError('use ** para potência, não ^')
    raise ValueError(
        f'operação não permitida, use apenas números, + - * / // % **, {", ".join(_FUNCTIONS)} e {", ".join(_CONSTANTS)}'
    )
