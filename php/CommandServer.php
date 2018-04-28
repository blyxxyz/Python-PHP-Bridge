<?php
declare(strict_types=1);

namespace blyxxyz\PythonServer;

/**
 * Process commands from another process
 *
 * This class allows another process to communicate with PHP and run PHP code.
 * It receives commands, executes them, and returns the result. The exact
 * method of communication should be defined in inheriting classes, but it's
 * assumed to use JSON or some other format that maps to arrays, strings and
 * numbers.
 */
abstract class CommandServer
{
    /** @var ObjectStore */
    private $objectStore;

    public function __construct()
    {
        $this->objectStore = new ObjectStore();
    }

    /**
     * Receive a command from the other side of the bridge
     *
     * Waits for a command. If one is received, returns it. If the other side
     * is closed, return false.
     *
     * @psalm-suppress MismatchingDocblockReturnType
     * @return array{cmd: string, data: mixed}|false
     */
    abstract protected function receive(): array;

    /**
     * Send a response to the other side of the bridge
     *
     * @param array $data
     *
     * @return void
     */
    abstract protected function send(array $data);

    /**
     * Encode a value into something JSON-serializable
     *
     * @param mixed $data
     *
     * @return array{type: string, value: mixed}
     */
    protected function encode($data): array
    {
        if (is_int($data) || is_string($data) || is_null($data) ||
            is_bool($data)) {
            return [
                'type' => gettype($data),
                'value' => $data
            ];
        } elseif (is_float($data)) {
            if (is_nan($data) || is_infinite($data)) {
                $data = (string)$data;
            }
            return [
                'type' => 'double',
                'value' => $data
            ];
        } elseif (is_array($data)) {
            return [
                'type' => 'array',
                'value' => array_map([$this, 'encode'], $data)
            ];
        } elseif (is_object($data)) {
            return [
                'type' => 'object',
                'value' => [
                    'class' => get_class($data),
                    'hash' => $this->objectStore->encode($data)
                ]
            ];
        } elseif (is_resource($data)) {
            return [
                'type' => 'resource',
                'value' => [
                    'type' => get_resource_type($data),
                    'hash' => $this->objectStore->encode($data)
                ]
            ];
        } else {
            $type = gettype($data);
            throw new \Exception("Can't encode value of type '$type'");
        }
    }

    /**
     * Convert deserialized data into the value it represents, inverts encode
     *
     * @param array{type: string, value: mixed} $data
     *
     * @return mixed
     */
    protected function decode(array $data)
    {
        $type = $data['type'];
        $value = $data['value'];
        switch ($type) {
            case 'integer':
            case 'string':
            case 'NULL':
            case 'boolean':
                return $value;
            case 'double':
                if ($value === 'NAN') {
                    return NAN;
                } elseif ($value === 'INF') {
                    return INF;
                }
                return $value;
            case 'array':
                return $this->decodeArray($value);
            case 'object':
            case 'resource':
                return $this->objectStore->decode($value['hash']);
            default:
                throw new \Exception("Unknown type '$type'");
        }
    }

    /**
     * Decode an array of values
     *
     * @param array<array> $dataItems
     *
     * @return array
     */
    protected function decodeArray(array $dataItems)
    {
        return array_map([$this, 'decode'], $dataItems);
    }

    /**
     * Continually listen for commands
     *
     * @return void
     */
    public function communicate()
    {
        while (($command = $this->receive()) !== false) {
            $cmd = $command['cmd'];
            $data = $command['data'];
            try {
                $response = $this->encode($this->execute($cmd, $data));
            } catch (\Throwable $exception) {
                $response = [
                    'type' => 'thrownException',
                    'value' => $this->encode($exception),
                    'message' => $exception->getMessage()
                ];
            }
            $this->send($response);
        }
    }

    /**
     * Execute a command and return the (unencoded) result
     *
     * @param string $command The name of the command
     * @param mixed $data The parameters of the commands
     *
     * @return mixed
     */
    private function execute(string $command, $data)
    {
        switch ($command) {
            case 'getConst':
                return Commands::getConst($data);
            case 'setConst':
                return Commands::setConst(
                    $data['name'],
                    $this->decode($data['value'])
                );
            case 'getGlobal':
                return Commands::getGlobal($data);
            case 'setGlobal':
                return Commands::setGlobal(
                    $data['name'],
                    $this->decode($data['value'])
                );
            case 'callFun':
                return Commands::callFun(
                    $data['name'],
                    $this->decodeArray($data['args'])
                );
            case 'callObj':
                return Commands::callObj(
                    $this->decode($data['obj']),
                    $this->decodeArray($data['args'])
                );
            case 'callMethod':
                return Commands::callMethod(
                    $this->decode($data['obj']),
                    $data['name'],
                    $this->decodeArray($data['args'])
                );
            case 'hasItem':
                return Commands::hasItem(
                    $this->decode($data['obj']),
                    $this->decode($data['offset'])
                );
            case 'getItem':
                return Commands::getItem(
                    $this->decode($data['obj']),
                    $this->decode($data['offset'])
                );
            case 'setItem':
                return Commands::setItem(
                    $this->decode($data['obj']),
                    $this->decode($data['offset']),
                    $this->decode($data['value'])
                );
            case 'delItem':
                return Commands::delItem(
                    $this->decode($data['obj']),
                    $this->decode($data['offset'])
                );
            case 'createObject':
                return Commands::createObject(
                    $data['name'],
                    $this->decodeArray($data['args'])
                );
            case 'getProperty':
                return Commands::getProperty(
                    $this->decode($data['obj']),
                    $data['name']
                );
            case 'setProperty':
                return Commands::setProperty(
                    $this->decode($data['obj']),
                    $data['name'],
                    $this->decode($data['value'])
                );
            case 'listProperties':
                return Commands::listProperties($this->decode($data));
            case 'classInfo':
                return Commands::classInfo($data);
            case 'listConsts':
                return Commands::listConsts();
            case 'listGlobals':
                return Commands::listGlobals();
            case 'listFuns':
                return Commands::listFuns();
            case 'listClasses':
                return Commands::listClasses();
            case 'resolveName':
                return Commands::resolveName($data);
            case 'repr':
                return Commands::repr($this->decode($data));
            case 'str':
                return Commands::str($this->decode($data));
            case 'count':
                return Commands::count($this->decode($data));
            case 'startIteration':
                return Commands::startIteration($this->decode($data));
            case 'nextIteration':
                return Commands::nextIteration($this->decode($data));
            default:
                throw new \Exception("Unknown command '$command'");
        }
    }
}
