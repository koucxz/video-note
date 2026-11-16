/**
 * 渲染前给 LLM 产出的 Markdown 做一次规范化。
 *
 * react-markdown（CommonMark + GFM）对空行很挑：表格和围栏代码块如果紧贴上一行
 * 文字出现，就不会被识别成块级结构，结果表格挤成一堆竖线、代码块把后面整篇吃进去。
 * 模型生成时经常漏这一行空行，所以这里统一补齐，而不是去改提示词碰运气。
 *
 * 只做「补空行 / 拼分隔行 / 补闭合围栏」这类无副作用的结构修补，不改写正文内容。
 */

const FENCE_RE = /^\s{0,3}(`{3,}|~{3,})/
const TABLE_ROW_RE = /^\s*\|.*\|\s*$/
const DELIM_ROW_RE = /^[\s|:-]*-[\s|:-]*$/
const LIST_ITEM_RE = /^\s{0,3}([-*+]|\d{1,9}[.)])\s+\S/
const HEADING_RE = /^\s{0,3}(#{1,6})([^\s#])/

const isFence = (line) => FENCE_RE.test(line)
const isTableRow = (line) => TABLE_ROW_RE.test(line)
const isDelimRow = (line) => line.includes('|') && DELIM_ROW_RE.test(line)
const isListItem = (line) => LIST_ITEM_RE.test(line)
const isHeading = (line) => /^\s{0,3}#{1,6}\s+\S/.test(line)

/** 数一列表行有几列（去掉首尾空单元） */
function columnCount(line) {
  return line.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').length
}

/** 没有分隔行的表格补一行 `| --- | --- |`，否则 GFM 不认 */
function delimiterFor(row) {
  return '| ' + Array.from({ length: columnCount(row) }, () => '---').join(' | ') + ' |'
}

export function normalizeMarkdown(input) {
  if (!input) return ''
  let text = String(input).replace(/\r\n?/g, '\n')

  // 整篇被模型包进 ```markdown … ``` 时先剥掉外层，不然整篇渲染成一个代码块
  const outer = text.match(/^\s*(`{3,}|~{3,})[ \t]*([A-Za-z0-9_-]*)[ \t]*\n([\s\S]*?)\n?[ \t]*\1[ \t]*\s*$/)
  if (outer && (!outer[2] || /^(markdown|md|text|plaintext|gfm)$/i.test(outer[2]))) {
    text = outer[3]
  }

  const lines = text.split('\n')
  const out = []
  let fence = null          // 当前打开的围栏，例如 ```
  let tableOpen = false     // 上一行是否还是表格行

  const pushBlank = () => {
    if (out.length && out[out.length - 1] !== '') out.push('')
  }

  for (let i = 0; i < lines.length; i++) {
    let line = lines[i]

    // 「##标题」缺空格时 CommonMark 不认，补上
    line = line.replace(HEADING_RE, '$1 $2')

    // 围栏内部原样输出，只等闭合
    if (fence) {
      out.push(line)
      if (new RegExp('^\\s{0,3}' + fence[0] + '{3,}\\s*$').test(line)) fence = null
      continue
    }

    const opened = line.match(FENCE_RE)
    if (opened) {
      pushBlank()                 // 代码块前必须有空行
      fence = opened[1]
      tableOpen = false
      out.push(line)
      continue
    }

    if (isTableRow(line)) {
      if (!tableOpen) {
        pushBlank()               // 表格前必须有空行，否则不识别
        out.push(line)
        // 第二行不是分隔行就自己补一行，否则这张表只会显示成纯文本
        const next = lines[i + 1]
        if (next === undefined || !isTableRow(next) || !isDelimRow(next)) out.push(delimiterFor(line))
        tableOpen = true
      } else {
        out.push(line)
      }
      continue
    }
    tableOpen = false

    if (isHeading(line)) {
      pushBlank()                 // 标题紧贴上一段时部分解析器会并进段落
      out.push(line)
      continue
    }

    if (isListItem(line)) {
      // 只在列表「开头」补空行，条目之间补了会变成松散列表，条目里多出 <p>
      const prev = out.length ? out[out.length - 1] : ''
      if (prev !== '' && !isListItem(prev) && !/^\s{2,}/.test(prev)) pushBlank()
      out.push(line)
      continue
    }

    out.push(line)
  }

  // 围栏没闭合会把后面所有内容都当代码：补一个收尾
  if (fence) out.push(fence)

  return out.join('\n')
}
