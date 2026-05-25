<template>
  <div class="scene-graph">
    <div class="graph-row" v-for="(edge, index) in relations" :key="`${edge.source}-${edge.relation}-${edge.target}-${index}`">
      <span class="graph-node">{{ edge.source }}</span>
      <span class="graph-edge" :class="{ risky: edge.risk }">{{ edge.relation }}</span>
      <span class="graph-node" :class="{ risky: edge.risk }">{{ edge.target }}</span>
    </div>
  </div>
</template>

<script setup>
defineProps({
  relations: {
    type: Array,
    default: () => []
  }
})
</script>
