#include "FoliageAnchor.hpp"

#include "source/utilities/GeometryUtilities.hpp"
#include <algorithm>

namespace Mtree
{
namespace
{

float calculate_branch_length(const Node& node)
{
	float length = node.length;
	if (!node.children.empty())
		length += calculate_branch_length(node.children[0]->node);
	return length;
}

Vector3 get_side_child_position(const Node& parent, const NodeChild& child,
                               const Vector3& node_position)
{
	Vector3 tangent = Geometry::projected_on_plane(child.node.direction, parent.direction);
	if (tangent.squaredNorm() <= 1e-12f)
		tangent = parent.tangent;
	else
		tangent.normalize();
	return node_position + parent.direction * parent.length * child.position_in_parent +
	       tangent * parent.radius;
}

void extract_branch(const Node& node, const Vector3& node_position, const int branch_id,
                    const int hierarchy_depth, const float distance_along_branch,
                    const float branch_length, int& next_branch_id,
                    std::vector<FoliageAnchor>& anchors)
{
	const Vector3 end_position = node_position + node.direction * node.length;
	const float end_radius =
	    node.children.empty() ? node.radius : node.children[0]->node.radius;
	const float progress = std::clamp(
	    (distance_along_branch + node.length) / std::max(branch_length, 1e-6f), 0.0f, 1.0f);

	anchors.push_back(FoliageAnchor{
	    .position = end_position,
	    .direction = node.direction,
	    .radius = end_radius,
	    .hierarchy_depth = hierarchy_depth,
	    .branch_id = branch_id,
	    .branch_progress = progress,
	});

	if (node.children.empty())
		return;

	extract_branch(node.children[0]->node, end_position, branch_id, hierarchy_depth,
	               distance_along_branch + node.length, branch_length, next_branch_id, anchors);

	for (size_t index = 1; index < node.children.size(); ++index)
	{
		const NodeChild& child = *node.children[index];
		const Vector3 child_position = get_side_child_position(node, child, node_position);
		const int child_branch_id = next_branch_id++;
		anchors.push_back(FoliageAnchor{
		    .position = child_position,
		    .direction = child.node.direction,
		    .radius = child.node.radius,
		    .hierarchy_depth = hierarchy_depth + 1,
		    .branch_id = child_branch_id,
		    .branch_progress = 0.0f,
		});
		extract_branch(child.node, child_position, child_branch_id, hierarchy_depth + 1, 0.0f,
		               calculate_branch_length(child.node), next_branch_id, anchors);
	}
}

} // namespace

std::vector<FoliageAnchor> extract_foliage_anchors(Tree& tree)
{
	std::vector<FoliageAnchor> anchors;
	int next_branch_id = 0;
	for (const Stem& stem : tree.get_stems())
	{
		const int branch_id = next_branch_id++;
		extract_branch(stem.node, stem.position, branch_id, 0, 0.0f,
		               calculate_branch_length(stem.node), next_branch_id, anchors);
	}
	return anchors;
}

} // namespace Mtree
