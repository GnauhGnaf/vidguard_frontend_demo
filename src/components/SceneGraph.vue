<template>
  <div class="scene-graph">
    <template v-if="inferImageSrc">
      <img :src="inferImageSrc" alt="推理分析图" class="scene-graph-infer-image" />
    </template>
    <template v-else>
      <div class="graph-row" v-for="(edge, index) in relations" :key="`${edge.source}-${edge.relation}-${edge.target}-${index}`">
        <span class="graph-node">{{ edge.source }}</span>
        <span class="graph-edge" :class="{ risky: edge.risk }">{{ edge.relation }}</span>
        <span class="graph-node" :class="{ risky: edge.risk }">{{ edge.target }}</span>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  relations: {
    type: Array,
    default: () => []
  },
  caseId: {
    type: String,
    default: ''
  }
})

const inferImageMap = {
  'metaphor-risk': '/demo-data/metorphor_infer.png',
  'safe-video': '/demo-data/safe_infer.png',
  'literal-risk': '/demo-data/harmful.png'
}
const inferImageSrc = computed(() => inferImageMap[props.caseId] || null)
</script>
