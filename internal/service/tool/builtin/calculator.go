package builtin

import (
	"fmt"
	"go/ast"
	"go/parser"
	"go/token"
	"math"
	"strconv"
)

type CalculatorTool struct{}

func NewCalculatorTool() *CalculatorTool {
	return &CalculatorTool{}
}

func (t *CalculatorTool) Name() string {
	return "calculator"
}

func (t *CalculatorTool) Description() string {
	return "执行数学计算。支持基本四则运算和常用数学函数。"
}

func (t *CalculatorTool) InputSchema() map[string]interface{} {
	return map[string]interface{}{
		"type": "object",
		"properties": map[string]interface{}{
			"expression": map[string]interface{}{
				"type":        "string",
				"description": "数学表达式，如 '2 + 3 * 4' 或 'sqrt(16)'",
			},
		},
		"required": []string{"expression"},
	}
}

func (t *CalculatorTool) Execute(args map[string]interface{}) (interface{}, error) {
	expr, ok := args["expression"].(string)
	if !ok || expr == "" {
		return nil, fmt.Errorf("缺少数学表达式")
	}

	result, err := evalExpression(expr)
	if err != nil {
		return nil, fmt.Errorf("计算失败: %w", err)
	}

	return map[string]interface{}{
		"expression": expr,
		"result":     result,
	}, nil
}

func evalExpression(expr string) (float64, error) {
	node, err := parser.ParseExpr(expr)
	if err != nil {
		return 0, err
	}
	return evalNode(node)
}

func evalNode(node ast.Expr) (float64, error) {
	switch n := node.(type) {
	case *ast.BinaryExpr:
		left, err := evalNode(n.X)
		if err != nil {
			return 0, err
		}
		right, err := evalNode(n.Y)
		if err != nil {
			return 0, err
		}
		switch n.Op {
		case token.ADD:
			return left + right, nil
		case token.SUB:
			return left - right, nil
		case token.MUL:
			return left * right, nil
		case token.QUO:
			if right == 0 {
				return 0, fmt.Errorf("division by zero")
			}
			return left / right, nil
		default:
			return 0, fmt.Errorf("unsupported operator: %v", n.Op)
		}
	case *ast.BasicLit:
		if n.Kind == token.INT || n.Kind == token.FLOAT {
			return strconv.ParseFloat(n.Value, 64)
		}
		return 0, fmt.Errorf("unsupported literal: %v", n.Value)
	case *ast.CallExpr:
		fnName := fmt.Sprintf("%v", n.Fun)
		if fnName == "sqrt" && len(n.Args) == 1 {
			arg, err := evalNode(n.Args[0])
			if err != nil {
				return 0, err
			}
			return math.Sqrt(arg), nil
		}
		if fnName == "abs" && len(n.Args) == 1 {
			arg, err := evalNode(n.Args[0])
			if err != nil {
				return 0, err
			}
			return math.Abs(arg), nil
		}
		return 0, fmt.Errorf("unsupported function: %s", fnName)
	case *ast.ParenExpr:
		return evalNode(n.X)
	case *ast.UnaryExpr:
		val, err := evalNode(n.X)
		if err != nil {
			return 0, err
		}
		if n.Op == token.SUB {
			return -val, nil
		}
		return val, nil
	default:
		return 0, fmt.Errorf("unsupported expression type: %T", n)
	}
}
