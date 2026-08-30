# MY Location

A private Home Assistant custom integration for receiving the location of a Tesla vehicle through Tesla's official Fleet API / Fleet Telemetry infrastructure.

## Status

Early development. Version 0.1.0 currently provides the integration skeleton and Tesla OAuth setup. Device tracking and the Fleet Telemetry receiver will be added next.

## HACS installation

1. Open HACS in Home Assistant.
2. Add `ComputerEndProgram/MY-Location` as a custom repository of type **Integration**.
3. Install **MY Location**.
4. Restart Home Assistant.
5. Add Tesla application credentials under Home Assistant's Application Credentials settings.
6. Add the **MY Location** integration.

## Security

Do not commit Tesla client secrets, OAuth tokens, Home Assistant tokens, vehicle VINs, or private keys to this repository.

The Tesla virtual-key private key is intended to remain on the separately operated telemetry receiver and is not part of this repository's Home Assistant configuration.
