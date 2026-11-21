#pragma once

#include "Tree.hpp"

namespace Mtree
{

// Assign stable IDs across the complete graph before any mesher pruning. The first child is the
// continuation of its parent's branch; every side child starts a new branch.
void assign_branch_ids(Tree& tree);

} // namespace Mtree
