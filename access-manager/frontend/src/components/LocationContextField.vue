<script setup lang="ts">
import { useLocationContext } from '../composables/useLocationContext';

const { locationPathText } = useLocationContext();

function selectText(event: FocusEvent) {
  (event.target as HTMLInputElement).select();
}

</script>

<template>
  <div class="location-context-field">
    <input
      aria-label="Ubicación activa"
      :value="locationPathText"
      readonly
      @focus="selectText"
    />
  </div>
</template>
