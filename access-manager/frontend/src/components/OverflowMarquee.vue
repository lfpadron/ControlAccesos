<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue';

const props = defineProps<{ text: string }>();
const viewport = ref<HTMLElement | null>(null);
const track = ref<HTMLElement | null>(null);
const label = ref<HTMLElement | null>(null);
const overflowing = ref(false);
let observer: ResizeObserver | undefined;
let animation: Animation | undefined;
let lastMeasurement = '';

function measure() {
  if (!viewport.value || !track.value || !label.value) return;
  const available = viewport.value.clientWidth;
  const textWidth = label.value.getBoundingClientRect().width;
  const measurement = `${props.text}|${available}|${textWidth}`;
  // Identical polling results must not restart the initial pause or the loop.
  if (measurement === lastMeasurement) return;
  lastMeasurement = measurement;
  animation?.cancel();
  overflowing.value = available > 0 && textWidth > available;
  if (!overflowing.value) return;
  const distance = textWidth + 48;
  animation = track.value.animate(
    [{ transform: 'translateX(0)' }, { transform: `translateX(-${distance}px)` }],
    { delay: 1500, duration: distance / 40 * 1000, iterations: Infinity, easing: 'linear' },
  );
}

watch(() => props.text, measure, { flush: 'post' });
onMounted(() => {
  observer = new ResizeObserver(measure);
  observer.observe(viewport.value!);
  observer.observe(label.value!);
  measure();
});
onUnmounted(() => {
  observer?.disconnect();
  animation?.cancel();
});
</script>

<template>
  <span ref="viewport" class="overflow-marquee" :title="text">
    <span ref="track" class="overflow-marquee-track">
      <span ref="label">{{ text }}</span>
      <span v-if="overflowing" aria-hidden="true">{{ text }}</span>
    </span>
  </span>
</template>

<style scoped>
.overflow-marquee { display: block; min-width: 0; overflow: hidden; text-overflow: clip; white-space: nowrap; }
.overflow-marquee-track { display: inline-flex; gap: 48px; width: max-content; }
.overflow-marquee-track > span { flex: 0 0 auto; }
</style>
