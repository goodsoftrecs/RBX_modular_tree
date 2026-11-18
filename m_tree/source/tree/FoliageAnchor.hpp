#pragma once

#include "Tree.hpp"
#include <vector>

namespace Mtree
{

struct FoliageAnchor
{
	Vector3 position;
	Vector3 direction;
	float radius;
	int hierarchy_depth;
	int branch_id;
	float branch_progress;
};

std::vector<FoliageAnchor> extract_foliage_anchors(Tree& tree);

} // namespace Mtree

