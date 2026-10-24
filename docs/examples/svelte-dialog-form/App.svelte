<script>
  import { Dialog, Select } from 'bits-ui';

  let open = $state(false);
  let layout = $state('outside');
  let value = $state('consultation');
  let payload = $state('');
  let error = $state('');
  const items = [
    { value: 'consultation', label: 'Consultation' },
    { value: 'review', label: 'Review' },
  ];

  function capture(form) {
    payload = JSON.stringify(Object.fromEntries(new FormData(form)));
  }

  function submit(event) {
    event.preventDefault();
    capture(event.currentTarget);
    // Local scaffolding only: no booking server or validation request.
    error = 'This appointment is no longer available.';
  }
</script>

<h1>Booking form composition specimen</h1>
<label>
  Form layout
  <select bind:value={layout} onchange={() => { payload = ''; error = ''; }}>
    <option value="outside">Outer form with portal</option>
    <option value="inside">Form inside dialog</option>
  </select>
</label>

{#snippet controls()}
  <label for="customer">Customer</label>
  <input id="customer" name="customer" value="Synthetic customer" />
  <Select.Root type="single" bind:value name="service" {items}>
    <Select.Trigger type="button" aria-label="Service">{value}</Select.Trigger>
    <Select.Portal>
      <Select.Content>
        <Select.Viewport>
          {#each items as item}
            <Select.Item value={item.value} label={item.label}>{item.label}</Select.Item>
          {/each}
        </Select.Viewport>
      </Select.Content>
    </Select.Portal>
  </Select.Root>
  <button type="submit">Book appointment</button>
  <p role="alert">{error}</p>
{/snippet}

{#snippet dialog()}
  <Dialog.Root bind:open>
    <Dialog.Trigger type="button">Choose appointment</Dialog.Trigger>
    <Dialog.Portal>
      <Dialog.Overlay class="overlay" />
      <Dialog.Content class="dialog">
        <Dialog.Title>Book appointment</Dialog.Title>
        <Dialog.Description>
          Synthetic local form ownership check, not a production integration.
        </Dialog.Description>
        {#if layout === 'inside'}
          <form onsubmit={submit}>{@render controls()}</form>
        {:else}
          {@render controls()}
          <button type="button" onclick={() => capture(document.getElementById('booking'))}>
            Inspect outer form data
          </button>
        {/if}
        <Dialog.Close type="button">Cancel</Dialog.Close>
      </Dialog.Content>
    </Dialog.Portal>
  </Dialog.Root>
{/snippet}

{#if layout === 'outside'}
  <form id="booking" onsubmit={submit}>{@render dialog()}</form>
{:else}
  {@render dialog()}
{/if}
<output>{payload}</output>

<style>
  :global(body) { font: 18px system-ui; margin: 24px; }
  :global(button), :global(input), :global(select) {
    font: inherit; padding: 8px; margin: 8px; max-width: 90%;
  }
  :global(.overlay) { position: fixed; inset: 0; background: #0008; }
  :global(.dialog) {
    position: fixed; top: 10%; left: 5%; width: 80%; max-width: 500px;
    padding: 16px; background: white; border: 1px solid black;
  }
  :global([data-select-content]) { background: white; border: 1px solid black; z-index: 100; }
  :global([data-highlighted]) { background: #ddd; }
</style>
