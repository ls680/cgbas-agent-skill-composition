# Claim boundary / 论文结论边界

## The practical problem

A deployed composition can fail at one interface even though its component
Skills each retain successful execution evidence. Editing a shared Skill expands
the regression surface, rejecting the composition loses capability, and rolling
back the complete chain discards unrelated calls. Paper 13 tests whether the
diagnosed handoff itself can be repaired as a versioned, auditable invocation
adapter.

实际问题是：多个已有成功证据的 Skill 被组合后，仍可能在一个交接接口上失败。修改共享
Skill 会扩大回归范围，拒绝组合会损失能力，整链回滚会丢弃无关调用。本文检验能否把
修复限制在已诊断交接处，并生成可版本化、可审计的调用适配器。

## What CGBAS does

- restores the complete missing successful prefix before a fixed consumer;
- invokes a provenance-linked role-compatible consumer wrapper;
- prevents a diagnosed non-goal destructive call before it executes; and
- leaves a healthy composition and all unaffected call identities unchanged.

CGBAS 分别恢复缺失的成功前缀、调用有来源证据且角色一致的消费端包裹、在执行前阻止
已诊断的非目标破坏调用，并保持健康组合与所有未受影响调用身份不变。

## Preconditions for the claim

- the conflict class and boundary are correctly diagnosed;
- a successful and still-current provenance witness is retained;
- the native environment can be reset and exposes a goal outcome;
- the failure is one of the four controlled interface regressions in scope; and
- locality is measured at the call boundary, not as a constant action budget.

结论依赖正确诊断、仍然有效的成功见证、可重置且具有原生目标判定的环境，以及本文覆盖
的四类受控接口回归。局部性是调用边界意义上的，不等于固定或很低的动作成本。

## What the paper does not establish

The experiment does not estimate production prevalence, discover new failure
operators, repair arbitrary failures without provenance, prove robustness under
API drift, or show that an adapter is always preferable to replanning or rollback.
Its independent confirmation transfers the frozen mechanism to new task
identifiers; it does not transfer to unseen mutation operators.

本实验不估计生产故障发生率，不发现新的故障算子，不处理无来源证据的任意失败，不证明
API 漂移下仍可靠，也不声称适配器总是优于重新规划或回滚。独立确认验证的是冻结机制向
新任务标识迁移，而不是向未见故障算子迁移。
