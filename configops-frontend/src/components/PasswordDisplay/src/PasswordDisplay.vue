<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElButton, ElMessage } from 'element-plus'
import { Icon } from '@/components/Icon'
import { propTypes } from '@/utils/propTypes'
import { useDesign } from '@/hooks/web/useDesign'
import { useI18n } from '@/hooks/web/useI18n'

const { getPrefixCls } = useDesign()
const { t } = useI18n()

const prefixCls = getPrefixCls('password-display')

const props = defineProps({
  // 密码值
  value: propTypes.string.def(''),
  // 是否显示复制按钮
  showCopy: propTypes.bool.def(true),
  // 是否显示切换按钮
  showToggle: propTypes.bool.def(true),
  // 遮罩字符
  maskChar: propTypes.string.def('*'),
  // 最大显示长度
  maxLength: propTypes.number.def(20),
  // 是否默认显示密码
  defaultVisible: propTypes.bool.def(false)
})

// 是否显示密码
const isVisible = ref(props.defaultVisible)

// 显示的文本
const displayText = computed(() => {
  if (!props.value) return ''

  if (isVisible.value) {
    // 如果密码太长，截断并显示省略号
    return props.value.length > props.maxLength
      ? props.value.substring(0, props.maxLength) + '...'
      : props.value
  } else {
    // 显示遮罩字符
    return props.maskChar.repeat(Math.min(props.value.length, 8))
  }
})

// 切换显示/隐藏
const toggleVisibility = () => {
  isVisible.value = !isVisible.value
}

// 复制密码
const copyPassword = async () => {
  if (!props.value) {
    ElMessage.warning(t('common.noData'))
    return
  }

  try {
    await navigator.clipboard.writeText(props.value)
    ElMessage.success(t('common.copySuccess'))
  } catch (err) {
    // 降级方案：使用传统的复制方法
    const textArea = document.createElement('textarea')
    textArea.value = props.value
    document.body.appendChild(textArea)
    textArea.select()
    try {
      document.execCommand('copy')
      ElMessage.success(t('common.copySuccess'))
    } catch (fallbackErr) {
      ElMessage.error(t('common.copyFailed'))
    }
    document.body.removeChild(textArea)
  }
}
</script>

<template>
  <div :class="prefixCls" class="inline-flex items-center gap-2">
    <!-- 密码文本 -->
    <span
      :class="`${prefixCls}__text`"
      class="font-mono text-sm select-none"
      :title="isVisible ? value : ''"
    >
      {{ displayText }}
    </span>

    <!-- 操作按钮组 -->
    <div :class="`${prefixCls}__actions`" class="inline-flex gap-1">
      <!-- 显示/隐藏切换按钮 -->
      <ElButton
        v-if="showToggle && value"
        type="text"
        size="small"
        @click="toggleVisibility"
        class="!p-1 !min-h-6 !min-w-6"
      >
        <Icon :icon="isVisible ? 'vi-ep:hide' : 'vi-ep:view'" :size="12" />
      </ElButton>

      <!-- 复制按钮 -->
      <ElButton
        v-if="showCopy && value"
        type="text"
        size="small"
        @click="copyPassword"
        class="!p-1 !min-h-6 !min-w-6"
      >
        <Icon icon="vi-ep:copy-document" :size="12" />
      </ElButton>
    </div>
  </div>
</template>

<style lang="less" scoped>
@prefix-cls: ~'@{adminNamespace}-password-display';

.@{prefix-cls} {
  position: relative;
  z-index: 10;

  &__text {
    min-width: 60px;
    max-width: 200px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  &__actions {
    opacity: 0.7;
    transition: opacity 0.2s;
    position: relative;
    z-index: 20;

    &:hover {
      opacity: 1;
    }

    :deep(.el-button) {
      position: relative;
      z-index: 30;
      border: none;
      background: transparent;
      padding: 2px;

      &:hover {
        background-color: var(--el-color-primary-light-9);
        border-radius: 4px;
      }
    }
  }
}

// 表格行悬停时显示操作按钮
:deep(.el-table__row:hover) {
  .@{prefix-cls}__actions {
    opacity: 1;
  }
}

// 确保在表格中有足够的层级
:deep(.el-table) {
  .@{prefix-cls} {
    position: relative;
    z-index: 10;
  }
}
</style>
