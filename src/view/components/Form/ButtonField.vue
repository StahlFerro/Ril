<template>
  <a
    :id="id"
    :v-click-outside="listenToOutsideClicks? emitClickOutside : null"
    class="button" :class="{
      'is-neon-white': color == 'white',
      'is-neon-emerald': color == 'green',
      'is-neon-cyan': color == 'cyan',
      'is-neon-crimson': color == 'red',
      'is-neon-cobalt': color == 'blue',
      'is-neon-sunset': color == 'orange',
      'is-neon-purple': color == 'purple',
      'is-loading': isLoading,
      'square-button': isSquare,
      'non-interactive': isNonInteractive,
      'is-small': size == 'small',
      'is-medium': size == 'medium',
      'is-large': size == 'large',
      'is-active': isActive,
      'text-padding-small': textPadding == 'small'
    }"
    :title="hint" @click="$emit('click', $event)"
  >
    <span v-if="icons.length >= 2" class="icon" :class="{
      'is-small': iconSize == 'small',
      'is-medium': iconSize == 'medium',
    }">
      <font-awesome-icon :icon="icons" />
    </span>
    <span v-if="label">{{ label }}</span>
  </a>
</template>


<script>
  export default {
    name: "ButtonField",
    props: {
      id: {
        type: String,
        default: null,
        required: false,
      },
      icons: {
        type: Array,
        default() {
          return []
        },
        required: false,
      },
      label: {
        type: String,
        default: "",
        required: false,
      },
      color: {
        type: String,
        default: "white",
        required: false
      },
      size: {
        type: String,
        default: "normal",
        required: false,
      },
      iconSize: {
        type: String,
        default: "small",
        required: false,
      },
      textPadding: {
        type: String,
        default: "",
        required: false,
      },
      isSquare: {
        type: Boolean,
        default: false,
      },
      isActive: {
        type: Boolean,
        default: false
      },
      isLoading: {
        type: Boolean,
        default: false
      },
      isNonInteractive: {
        type: Boolean,
        default: false
      },
      hint: {
        type: String,
        default: "",
        required: false,
      },
      listenToOutsideClicks: {
        type: Boolean,
        default: false,
      }
    },
    emits: ['click', 'click-outside'],
    methods: {
      emitClickOutside(event) {
        console.debug('emitClickOutside');
        this.$emit('click-outside', event);
      }
    }
  };
</script>