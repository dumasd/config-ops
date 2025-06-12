<script setup lang="tsx">
import { Descriptions, DescriptionsSchema } from '@/components/Descriptions'
import { useI18n } from '@/hooks/web/useI18n'
import { ref, reactive, PropType } from 'vue'
import { ElRow, ElCol  } from 'element-plus'
import { ContentWrap } from '@/components/ContentWrap'
import { getChangesetApi } from '@/api/dashboard'
import { ChangelogItem } from '@/api/dashboard/types'
import { CodeEditor } from '@/components/CodeEditor'

const { t } = useI18n()

const props = defineProps({
  currentRow: {
    type: Object as PropType<ChangelogItem>
  },
  currentObjectId: {
    type: String
  }
})

const single_change = ref('')
const changes = ref([])

const schema = reactive<DescriptionsSchema[]>([])

const getChangesetDetail = () => {
    schema.length = 0
    changes.value = []
    if (!props.currentRow) return

    if (props.currentRow.system_type === 'NACOS') {
        schema.push(
            {
                field: 'namespace',
                label: t('changeset.namespace')
            },
            {
                field: 'group',
                label: t('changeset.group')
            },
            {
                field: 'dataId',
                label: t('changeset.dataId')
            },
            {
                field: 'format',
                label: t('changeset.format')
            }
        )
    } else if (props.currentRow.system_type === 'ELASTICSEARCH') { 
        schema.push(
            {
                field: 'method',
                label: t('changeset.method')
            },
            {
                field: 'path',
                label: t('changeset.path')
            }
        )
    } else if (props.currentRow.system_type === 'GRAPHDB') {
        schema.push(
            {
                field: 'type',
                label: t('changeset.type')
            },
            {
                field: 'dataset',
                label: t('changeset.dataset')
            }
        )
    } else if (props.currentRow.system_type === 'DATABASE') {
        //
    } else {
        return
    }

    const searchParams = {
        managed_object_id: props.currentObjectId,
        change_set_id: props.currentRow.change_set_id,
        system_id: props.currentRow.system_id,
        system_type: props.currentRow.system_type
    }

    getChangesetApi(searchParams).then((res) => {
        if (props.currentRow?.system_type === 'DATABASE') {
            single_change.value = String( res.data )
        } else {
            changes.value = res.data as []
        }
    })
}

const getProperty = (obj: any, key: string, defultValue: any) => {
    return (key in obj) ? obj[key] : defultValue;
}

getChangesetDetail()

const codeEditorOption = ref({
    fontSize: 12,
    minimap: { enabled: false },
    readOnly: true,
})

</script>

<template>
  <!-- NACOS -->
  <div v-if="props.currentRow?.system_type === 'NACOS'">
    <ContentWrap v-for="change, idx of changes" :key="idx" >
        <Descriptions
            :column="4"
            :data="change"
            :schema="schema"
        />
        <ElRow :gutter="10" justify="space-between" class="px-5">
            <ElCol :xl="12" :lg="12" :md="24" :sm="24" :xs="24">
                <CodeEditor :model-value="getProperty(change, 'patchContent', '')" :language="getProperty(change, 'format', '')" height="220px" width="98%" :language-selector="false" :theme-selector="false" :editor-option="codeEditorOption"/>
            </ElCol>
            <ElCol :xl="12" :lg="12" :md="24" :sm="24" :xs="24">
                <CodeEditor :model-value="getProperty(change, 'deleteContent', '')" :language="getProperty(change, 'format', '')" height="220px" width="98%" :language-selector="false" :theme-selector="false" :editor-option="codeEditorOption"/>
            </ElCol>
        </ElRow>
    </ContentWrap>
  </div>
  <!-- ELASTICSEARCH -->
  <div v-else-if="props.currentRow?.system_type === 'ELASTICSEARCH'">
    <ContentWrap v-for="change, idx of changes" :key="idx" >
        <Descriptions
            :column="4"
            :data="change"
            :schema="schema"
        />
        <ElRow :gutter="10" justify="space-between" class="px-5">
            <ElCol :xl="20" :lg="20" :md="24" :sm="24" :xs="24">
                <CodeEditor :model-value="getProperty(change, 'body', '')" language="json" height="220px" width="95%" :language-selector="false" :theme-selector="false" :editor-option="codeEditorOption"/>
            </ElCol>
        </ElRow>
    </ContentWrap>
  </div>
  <!-- GRAPHDB -->
  <div v-else-if="props.currentRow?.system_type === 'GRAPHDB'">
    <ContentWrap v-for="change, idx of changes" :key="idx" >
        <Descriptions
            :column="4"
            :data="change"
            :schema="schema"
        />
        <ElRow :gutter="10" justify="space-between" class="px-5">
            <ElCol :xl="20" :lg="20" :md="24" :sm="24" :xs="24">
                <CodeEditor :model-value="getProperty(change, 'query', '')" language="txt" height="220px" width="95%" :language-selector="false" :theme-selector="false" :editor-option="codeEditorOption"/>
            </ElCol>
        </ElRow>
    </ContentWrap>
  </div>  
  <div v-else-if="props.currentRow?.system_type === 'DATABASE'">
    <CodeEditor :model-value="single_change" language="sql" height="450px" width="95%" :language-selector="false" :theme-selector="false" :editor-option="codeEditorOption"/>
  </div>
</template>
