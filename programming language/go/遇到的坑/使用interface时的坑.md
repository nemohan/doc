# 使用interface时遇到的坑

在实现二叉查找树过程中，为了方便调试，写了一个输出二叉树结构的函数。为了便于输出函数可以输出普通的二叉查找树及平衡二叉查找树（AVL、红黑树）的结构，需每个二叉查找树的节点实现Node接口的方法

在测试过程中，第31行的代码left.Key()会导致panic。开始有点懵逼，因为底35行的left != nil已经检查了左孩子为空的情况，为什么会导致panic

因为忽略了left此时是Node接口类型，left != nil 检查的是接口自身是否为nil。而不是接口包含的指针是否为空

~~~go
type Node interface {
	Left() Node
	Right() Node
	Key() int
}

type BSTNode struct {
	v     interface{}
	k     int
	left  *BSTNode
	right *BSTNode
}

func (n *BSTNode) Left() Node {
	return n.left
}
func (n *BSTNode) Right() Node {
	return n.right
}
func (n *BSTNode) Key() int {
	return n.k
}

func dump(node Node, level int) {
	if node == nil {
		return
	}
	queue := []Node{node}
	fmt.Printf("level:%d %d\n", level, node.Key())
	for len(queue) > 0 {
		level++
		node := queue[0]
		left := node.Left()
		right := node.Right()
		if left != nil  {
            //left.Key() 导致panic
			fmt.Printf("left level:%d %d\n", level, left.Key())
			queue = append(queue, left)
		}
		if right != nil {
			fmt.Printf("right level:%d %d\n", level, right.Key())
			queue = append(queue, right)
		}
		queue = queue[1:]
	}
}
~~~



修复panic需要判断接口包含的指针是否为空。需要用到reflect.Value.IsNil 函数来检查

~~~go
func dump(node Node, level int) {
	if node == nil {
		return
	}
	queue := []Node{node}
	fmt.Printf("level:%d %d\n", level, node.Key())
	for len(queue) > 0 {
		level++
		node := queue[0]
		left := node.Left()
		right := node.Right()
		lv := reflect.ValueOf(left)
		rv := reflect.ValueOf(right)
		if left != nil && !lv.IsNil() {
			fmt.Printf("left level:%d %d\n", level, left.Key())
			queue = append(queue, left)
		}
		if right != nil && !rv.IsNil() {
			fmt.Printf("right level:%d %d\n", level, right.Key())
			queue = append(queue, right)
		}
		queue = queue[1:]
	}
}
~~~

