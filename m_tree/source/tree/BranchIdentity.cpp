#include "BranchIdentity.hpp"

namespace Mtree
{
namespace
{

void assign_node_branch_ids(Node& node, const int branch_id, int& next_branch_id)
{
	node.branch_id = branch_id;
	if (node.children.empty())
		return;

	assign_node_branch_ids(node.children[0]->node, branch_id, next_branch_id);
	for (size_t index = 1; index < node.children.size(); ++index)
	{
		const int child_branch_id = next_branch_id++;
		assign_node_branch_ids(node.children[index]->node, child_branch_id, next_branch_id);
	}
}

} // namespace

void assign_branch_ids(Tree& tree)
{
	int next_branch_id = 0;
	for (Stem& stem : tree.get_stems())
	{
		const int branch_id = next_branch_id++;
		assign_node_branch_ids(stem.node, branch_id, next_branch_id);
	}
}

} // namespace Mtree
