# NCBI 注释推断 TSS 数据构建技术方案（简版）

## 目标

本方案的目标是从 NCBI 获取可用于 TSS（转录起始位点）研究的基础数据。当前阶段只做数据源筛选和小规模验证，不直接下载全量基因组。

核心思路是：

```text
先找可用 assembly（基因组组装）
  -> 再确认它是否同时有 genome DNA、RNA/transcript、GFF3/GTF 注释
  -> 再考虑从 transcript 5' end 推断 TSS 候选点
```

这里得到的主要是 annotation-derived TSS（注释推断 TSS），不是实验测序直接确认的 true TSS（真实 TSS）。

## 第一步：获取 genome metadata（基因组元数据）

先不下载 FASTA、RNA、GFF3、GTF 大文件，只获取每个 assembly 的元数据。

原因：

- NCBI 中 assembly 数量很大，质量不统一。
- 有些 assembly 没有注释文件。
- 有些 assembly 只是 scaffold/contig 级别，序列连续性较差。
- 有些是 MAG（宏基因组组装基因组）或 atypical（非典型）样本，不适合作为第一版主数据。

第一版优先查询：

```text
bacteria（细菌）
RefSeq（参考序列数据库）
latest（最新版本）
annotated（有注释）
exclude atypical（排除非典型）
exclude MAG（排除宏基因组组装基因组）
```

获取字段：

```text
accession                         assembly 唯一登录号
organism-tax-id                   NCBI 分类编号
organism-name                     物种/菌株名称
source_database                   数据来源，确认是否为 RefSeq
assminfo-name                     assembly 名称
assminfo-level                    组装水平，如 Complete Genome / Scaffold / Contig
assminfo-refseq-category          RefSeq 分类，如 reference genome / representative genome
assminfo-status                   assembly 当前状态
assminfo-release-date             assembly 发布日期
assmstats-total-sequence-len      总序列长度，用于后续 FASTA 质控
annotinfo-name                    注释名称
annotinfo-status                  注释状态
annotinfo-release-date            注释发布日期
```

## 第二步：筛选 assembly

metadata 获取后，先根据字段筛选，不直接进入下载。

优先级建议：

```text
主数据候选：
  RefSeq
  current
  latest
  annotated
  reference genome 或 representative genome
  Complete Genome 或 Chromosome

扩展数据候选：
  RefSeq
  current
  latest
  annotated
  但不要求 reference/representative
  可包含 Scaffold / Contig

暂不纳入：
  GenBank-only
  MAG
  atypical
  无 annotation
```

这一步的产物应是 accession list（组装登录号列表），后续下载文件时使用。

## 第三步：下载成套文件

正式下载时，不能只下载 genome FASTA。为了从生物学角度推断 TSS，需要同一个 assembly 同时具备：

```text
genomic.fna        genome DNA 序列
rna.fna            RNA/transcript 序列
genomic.gff        GFF3 注释坐标
genomic.gtf        GTF 注释坐标
sequence_report    序列 ID 对应表
assembly report    assembly 元数据备份
```

关键点：

```text
有 GFF/GTF 不一定代表有可用 transcript sequence。
有 rna.fna 也不一定代表独立实验转录本证据。
如果 rna.fna 是由注释坐标导出的，它只能支持 annotation-derived TSS。
```

## 第四步：审计 RNA 与注释是否对应

下载后必须先检查：

```text
rna.fna 中有多少 RNA 序列
这些 RNA 是 mRNA、rRNA、tRNA、ncRNA 还是其他
RNA accession 是否能在 GFF3/GTF 中找到
GFF3/GTF 是否有 transcript 或 mRNA feature
GFF3/GTF 的 seqid 是否能对应 FASTA 中的序列 ID
```

只有 RNA、注释坐标、基因组序列能对应起来时，才进入 TSS 候选点提取。

> **重要说明**：NCBI 细菌的 `rna.fna` 通常**只包含 rRNA**（由 PGAP 预测），几乎没有 mRNA。因此对于大多数细菌 assembly，`rna.fna` **不能直接用于 mRNA 5' end 提取**，TSS 候选点主要依赖 GFF3/GTF 中的 `transcript`/`mRNA` feature 坐标推断，而非 RNA 序列比对。审计时如果发现 `rna.fna` 中全是 rRNA，属于正常情况，不应因此排除该 assembly。

## 第五步：推断 TSS 候选点

优先级：

```text
1. transcript/mRNA 5' end
   strand = + 时取 start
   strand = - 时取 end
   label_type = transcript_5end_annotation

2. RNA-to-genome alignment 5' end
   需要确认 RNA 序列包含真实 5' 端
   label_type = transcript_5end_alignment

3. gene 5' end
   只能作为 gene_start_proxy

4. CDS 5' end
   只能作为 cds_start_proxy
```

主数据应优先使用 transcript/mRNA 5' end。gene/CDS 起点只能作为弱标签，不能直接称为真实 TSS。

> **重要说明**：GFF3 中细菌的 `transcript` feature 本身就是由 PGAP 从 `gene`/`CDS` 推导出来的，因此 `transcript_5end_annotation` 与 `gene_start_proxy` 实际上往往是相同的。不应误认为 transcript 5' end 比 gene start 具有更强的独立证据——它们在细菌注释中本质上是同一来源。只有当存在独立实验转录本证据（如 RNA-seq 直接支持）时，transcript 5' end 才比 gene start 更可靠。

## 当前只做的小测试

当前只实现第一步的小规模测试：

```text
查询 bacteria 下 20 条 RefSeq annotated metadata
输出 JSONL
清理空行
转为 TSV
打印 Source Database、Assembly Level、Assembly Refseq Category 统计
```

该测试只验证 NCBI metadata 获取链路，不下载 genome/rna/gff3/gtf。

