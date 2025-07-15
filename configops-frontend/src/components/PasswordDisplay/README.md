# PasswordDisplay 组件

一个用于在表格中安全显示密码的Vue3组件，支持显示/隐藏切换和复制功能。

## 功能特性

- 🔒 默认隐藏密码，显示遮罩字符
- 👁️ 点击眼睛图标切换显示/隐藏密码
- 📋 一键复制密码到剪贴板
- 📱 响应式设计，适配不同屏幕尺寸
- 🎨 与Element Plus主题一致的样式
- ⚡ 支持长密码截断显示

## 基本用法

### 在表格中使用

```vue
<script setup lang="tsx">
import { PasswordDisplay } from '@/components/PasswordDisplay'

const tableColumns = [
  {
    field: 'password',
    label: '密码',
    width: 200,
    slots: {
      default: (data: any) => {
        return (
          <PasswordDisplay
            value={data.row.password}
            showCopy={true}
            showToggle={true}
            maxLength={20}
          />
        )
      }
    }
  }
]
</script>
```

### 在普通页面中使用

```vue
<template>
  <PasswordDisplay
    value="mySecretPassword123"
    :showCopy="true"
    :showToggle="true"
    :maxLength="15"
    maskChar="●"
  />
</template>
```

## API

### Props

| 参数 | 说明 | 类型 | 默认值 |
|------|------|------|--------|
| value | 密码值 | string | '' |
| showCopy | 是否显示复制按钮 | boolean | true |
| showToggle | 是否显示切换显示/隐藏按钮 | boolean | true |
| maskChar | 遮罩字符 | string | '*' |
| maxLength | 最大显示长度，超出部分显示省略号 | number | 20 |
| defaultVisible | 是否默认显示密码 | boolean | false |

### 样式定制

组件使用CSS变量，可以通过覆盖以下变量来自定义样式：

```css
.v-password-display {
  --password-text-color: var(--el-text-color-regular);
  --password-icon-color: var(--el-text-color-placeholder);
  --password-icon-hover-color: var(--el-color-primary);
}
```

## 注意事项

1. 组件已全局注册，可以直接在任何Vue文件中使用
2. 复制功能优先使用现代浏览器的 `navigator.clipboard` API，在不支持的浏览器中会降级使用传统方法
3. 在表格行悬停时，操作按钮会自动显示
4. 密码为空时，不会显示任何操作按钮

## 国际化

组件使用了以下国际化键值，请确保在你的语言包中定义：

```json
{
  "common": {
    "noData": "暂无数据",
    "copySuccess": "复制成功",
    "copyFailed": "复制失败"
  }
}
